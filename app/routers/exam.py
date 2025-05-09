from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Body, Query, UploadFile, File
from typing import Dict, Optional
import datetime
import logging
import os
import hashlib
import shutil

from app.schemas.exam import ExamDataSchema, SubmissionSchema, ResultSchema, AdminLoginSchema, ContentUpdateSchema
from app.services.parser import parsed_exam_data, parsed_correct_answers, reload_exam_data
from app.services.email_sender import send_results_emails # Importaremos depois

router = APIRouter()
logger = logging.getLogger(__name__)

# Credenciais admin - em produção usar variáveis de ambiente
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

# Mapeamento de índice de opção para letra (A, B, C, D)
OPTION_INDEX_TO_LETTER = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}

# Função para autenticar admin via body JSON
async def admin_auth(login: AdminLoginSchema = Body(...)):
    """Verifica se as credenciais de admin são válidas."""
    if login.username != ADMIN_USER or login.password != ADMIN_PASS:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return login.username

# Função para autenticar admin via query parameters
async def admin_auth_query(username: str = Query(...), password: str = Query(...)):
    """Verifica se as credenciais de admin são válidas (via query params)."""
    if username != ADMIN_USER or password != ADMIN_PASS:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return username

@router.get("/exam", response_model=ExamDataSchema)
def get_exam_data():
    """Retorna os dados da prova (metadados e questões)."""
    # SEMPRE recarrega os dados diretamente do disco para garantir que estejam atualizados
    reload_data, reload_answers = reload_exam_data()
    
    if not reload_data or not reload_data.questions:
        raise HTTPException(status_code=500, detail="Erro ao carregar os dados da prova.")
    
    # Log das questões carregadas
    logger.info(f"Retornando dados da prova: {len(reload_data.questions)} questões")
    for i, q in enumerate(reload_data.questions):
        logger.info(f"Q{q.question_number}: {q.text[:30]}... ({len(q.options)} opções)")
    
    return reload_data

@router.post("/submit", response_model=ResultSchema)
def submit_answers(submission: SubmissionSchema, background_tasks: BackgroundTasks):
    """Recebe as respostas, calcula o resultado e agenda o envio de e-mails."""
    # Recarrega os dados para garantir consistência E USA OS DADOS RETORNADOS
    current_exam_data, current_answers = reload_exam_data()
    
    # Usa os dados retornados pela função reload_exam_data
    total_questions = len(current_exam_data.questions)
    logger.info(f"Processando submissão. Total de questões: {total_questions}, Total de respostas: {len(submission.answers)}")
    
    # Log das questões que estão carregadas (usando a variável local)
    for q in current_exam_data.questions:
        logger.info(f"Questão carregada: Q{q.question_number}: {q.text[:30]}...")
    
    # Esta verificação pode não ser mais necessária ou precisar de ajuste
    # if total_questions != 10 and len(submission.answers) == 10: ... 
    
    correct_count = 0
    incorrect_questions_details = []

    submitted_answers_map = {ans.question_number: ans.selected_option_index for ans in submission.answers}
    
    if len(submission.answers) != total_questions:
        error_msg = f"Número de respostas ({len(submission.answers)}) não confere com o número de questões ({total_questions})"
        logger.error(error_msg)
        # Ajuste para permitir a continuação mesmo com número diferente
        # if len(submission.answers) >= total_questions or len(submission.answers) == 10: ...
        # Considere ser mais estrito aqui ou ajustar a lógica
        if len(submission.answers) < total_questions:
            logger.warning("Número de respostas menor que o número de questões. Continuando...")
        elif len(submission.answers) > total_questions:
             raise HTTPException(status_code=400, detail=error_msg)
             
    # Itera sobre as questões CORRENTES carregadas
    for question in current_exam_data.questions:
        q_num = question.question_number
        # Usa o gabarito CORRENTE carregado
        correct_answer_letter = current_answers.get(q_num)

        if correct_answer_letter is None:
            logger.error(f"Gabarito não encontrado para a questão {q_num}.")
            continue

        submitted_index = submitted_answers_map.get(q_num)
        submitted_letter = OPTION_INDEX_TO_LETTER.get(submitted_index) if submitted_index is not None else None

        if submitted_letter == correct_answer_letter:
            correct_count += 1
        else:
            # Encontra o texto da resposta correta e da resposta enviada
            correct_option_text = ""
            submitted_option_text = ""
            
            for i, option_text in enumerate(question.options):
                option_letter = OPTION_INDEX_TO_LETTER.get(i)
                if option_letter == correct_answer_letter:
                    correct_option_text = f"{option_letter}) {option_text}"
                if submitted_index is not None and i == submitted_index:
                    submitted_option_text = f"{option_letter}) {option_text}"
            
            incorrect_questions_details.append({
                "question_number": q_num,
                "text": question.text,
                "correct_answer_text": correct_option_text,
                "submitted_answer_text": submitted_option_text
            })

    # Adiciona tratamento para caso extremo onde nenhuma questão foi processada
    if len(current_exam_data.questions) == 0:
        logger.critical("ALERTA: Nenhuma questão carregada! Isso é um erro crítico.")
        raise HTTPException(status_code=500, detail="Erro crítico: Nenhuma questão carregada no sistema")

    score = (correct_count / max(total_questions, 1)) * 100
    
    # Log detalhado das respostas
    logger.info(f"Score: {score}, Corretas: {correct_count}, Total: {total_questions}")

    result = ResultSchema(
        score=round(score, 2),
        correct_answers=correct_count,
        total_questions=total_questions, # Usa o total_questions calculado corretamente
        incorrect_questions=incorrect_questions_details
    )

    # Agenda o envio de e-mails em background para não bloquear a resposta
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    background_tasks.add_task(
        send_results_emails,
        student_identifier=submission.student_identifier,
        result=result,
        # Usa o título dos dados CORRENTES
        exam_title=current_exam_data.metadata.titulo,
        timestamp=timestamp
    )

    return result

@router.post("/admin/login")
async def admin_login(login_data: AdminLoginSchema):
    """Endpoint para autenticação administrativa."""
    try:
        admin_username = await admin_auth(login_data)
        return {"success": True, "username": admin_username}
    except HTTPException:
        raise

@router.post("/admin/update-content")
async def update_content(content_data: ContentUpdateSchema, admin: str = Depends(admin_auth)):
    """Atualiza o conteúdo da prova e/ou gabarito."""
    try:
        # Atualiza os arquivos
        if content_data.exam_content:
            with open("app/exam.md", "w", encoding="utf-8") as f:
                f.write(content_data.exam_content)
        
        if content_data.answers_content:
            with open("app/gabarito.md", "w", encoding="utf-8") as f:
                f.write(content_data.answers_content)
        
        # Recarrega os dados da prova
        reload_exam_data()
        
        return {"success": True, "message": "Conteúdo atualizado com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao atualizar conteúdo: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar conteúdo: {str(e)}")

@router.get("/admin/current-content")
async def get_current_content(admin: str = Depends(admin_auth_query)):
    """Retorna o conteúdo atual da prova e do gabarito."""
    try:
        exam_content = ""
        answers_content = ""
        
        if os.path.exists("app/exam.md"):
            with open("app/exam.md", "r", encoding="utf-8") as f:
                exam_content = f.read()
        
        if os.path.exists("app/gabarito.md"):
            with open("app/gabarito.md", "r", encoding="utf-8") as f:
                answers_content = f.read()
        
        return {
            "exam_content": exam_content,
            "answers_content": answers_content
        }
    except Exception as e:
        logger.error(f"Erro ao ler conteúdo: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao ler conteúdo: {str(e)}")

@router.post("/admin/update-content-query")
async def update_content_query(
    exam_content: Optional[str] = Body(None),
    answers_content: Optional[str] = Body(None),
    admin: str = Depends(admin_auth_query)
):
    """Atualiza o conteúdo da prova e/ou gabarito usando query params para autenticação."""
    try:
        # Atualiza os arquivos
        if exam_content is not None:  # Permite conteúdo vazio
            logger.info(f"Atualizando arquivo de exame com {len(exam_content)} bytes")
            with open("app/exam.md", "w", encoding="utf-8") as f:
                f.write(exam_content)
        
        if answers_content is not None:  # Permite conteúdo vazio
            logger.info(f"Atualizando arquivo de gabarito com {len(answers_content)} bytes")
            with open("app/gabarito.md", "w", encoding="utf-8") as f:
                f.write(answers_content)
        
        # Força a recarga dos dados
        logger.info("Forçando recarga dos dados após atualização...")
        new_exam_data, new_answers = reload_exam_data()
        
        # Verifica se a recarga foi bem-sucedida
        logger.info(f"Verificando recarga: {len(new_exam_data.questions)} questões")
        
        return {
            "success": True, 
            "message": "Conteúdo atualizado com sucesso",
            "questions_count": len(new_exam_data.questions),
            "answers_count": len(new_answers)
        }
    except Exception as e:
        logger.error(f"Erro ao atualizar conteúdo: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar conteúdo: {str(e)}")

@router.post("/admin/upload-exam")
async def upload_exam_file(
    file: UploadFile = File(...),
    admin: str = Depends(admin_auth_query)
):
    """Faz upload de um arquivo MD para o conteúdo do exame."""
    try:
        if not file.filename.endswith('.md'):
            raise HTTPException(status_code=400, detail="Apenas arquivos Markdown (.md) são permitidos")
        
        # Salva o arquivo temporário
        with open("app/exam.md", "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Força a recarga dos dados
        logger.info("Forçando recarga dos dados após upload do arquivo de exame...")
        new_exam_data, new_answers = reload_exam_data()
        
        return {
            "success": True, 
            "message": "Arquivo de exame enviado com sucesso",
            "filename": file.filename,
            "questions_count": len(new_exam_data.questions)
        }
    except Exception as e:
        logger.error(f"Erro ao fazer upload do arquivo de exame: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload do arquivo: {str(e)}")

@router.post("/admin/upload-answers")
async def upload_answers_file(
    file: UploadFile = File(...),
    admin: str = Depends(admin_auth_query)
):
    """Faz upload de um arquivo MD para o gabarito."""
    try:
        if not file.filename.endswith('.md'):
            raise HTTPException(status_code=400, detail="Apenas arquivos Markdown (.md) são permitidos")
        
        # Salva o arquivo temporário
        with open("app/gabarito.md", "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Força a recarga dos dados
        logger.info("Forçando recarga dos dados após upload do arquivo de gabarito...")
        new_exam_data, new_answers = reload_exam_data()
        
        return {
            "success": True, 
            "message": "Arquivo de gabarito enviado com sucesso",
            "filename": file.filename,
            "answers_count": len(new_answers)
        }
    except Exception as e:
        logger.error(f"Erro ao fazer upload do arquivo de gabarito: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload do arquivo: {str(e)}")
