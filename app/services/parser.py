import re
import logging
from pathlib import Path
from typing import Tuple, Dict, List

from app.schemas.exam import ExamDataSchema, QuestionSchema, ExamMetadataSchema

logger = logging.getLogger(__name__)

EXAM_FILE = Path("app/exam.md")
GABARITO_FILE = Path("app/gabarito.md")

def parse_exam_files() -> Tuple[ExamDataSchema, Dict[int, str]]:
    """Lê e parseia os arquivos exam.md e gabarito.md."""
    logger.info(f"Carregando arquivos de prova: {EXAM_FILE} e {GABARITO_FILE}")
    
    # Lê os arquivos diretamente do disco para garantir conteúdo atualizado
    try:
        exam_content = EXAM_FILE.read_text(encoding='utf-8')
        gabarito_content = GABARITO_FILE.read_text(encoding='utf-8')
        
        logger.info(f"Arquivos carregados. Tamanho do conteúdo da prova: {len(exam_content)} bytes")
        logger.debug(f"Primeiros 200 caracteres do conteúdo: {exam_content[:200]}")
    except Exception as e:
        logger.error(f"Erro ao ler arquivos: {e}")
        raise
    
    # Parse Metadata (Manual)
    metadata_match = re.search(r"^---\s*$(.*?)^---\s*$", exam_content, re.MULTILINE | re.DOTALL)
    metadata_dict = {}
    if metadata_match:
        metadata_str = metadata_match.group(1)
        for line in metadata_str.strip().split('\n'):
            if ':' in line:  # Garantir que a linha tenha o formato correto
                key, value = line.split(':', 1)
                metadata_dict[key.strip()] = value.strip()
    
    # Valores padrão caso falte algum campo obrigatório
    if 'id' not in metadata_dict:
        metadata_dict['id'] = 'default_id'
    if 'titulo' not in metadata_dict:
        metadata_dict['titulo'] = 'Prova Sem Título'
    if 'duracao_min' not in metadata_dict:
        metadata_dict['duracao_min'] = '60'
    
    # Conversão de tipos
    if 'duracao_min' in metadata_dict:
        try:
            metadata_dict['duracao_min'] = int(metadata_dict['duracao_min'])
        except ValueError:
            metadata_dict['duracao_min'] = 60
    
    logger.info(f"Metadados extraídos: {metadata_dict}")
    
    metadata = ExamMetadataSchema(**metadata_dict)

    # Parse Questions - Novo método mais robusto
    questions_text = re.sub(r"^---\s*$(.*?)^---\s*$", '', exam_content, flags=re.MULTILINE | re.DOTALL).strip()
    
    # Método alternativo para encontrar questões
    question_pattern = re.compile(r'Q(\d+)\.\s*(.*?)(?=(?:\n\s*Q\d+\.)|$)', re.DOTALL)
    raw_questions = question_pattern.findall(questions_text)
    
    logger.info(f"Método alternativo encontrou {len(raw_questions)} questões")
    
    questions = []
    for q_num_str, q_content in raw_questions:
        try:
            q_num = int(q_num_str)
            lines = q_content.strip().split('\n')
            q_text = lines[0].strip()
            
            # Extrai as opções (A, B, C, D)
            options = []
            for line in lines[1:]:
                line = line.strip()
                if re.match(r'^[A-D]\)', line):
                    options.append(line[3:].strip())
            
            if len(options) > 0:
                questions.append(QuestionSchema(question_number=q_num, text=q_text, options=options))
                logger.info(f"Questão {q_num} processada com {len(options)} opções")
            else:
                logger.warning(f"Questão {q_num} ignorada - sem opções")
        except Exception as e:
            logger.error(f"Erro ao processar questão {q_num_str}: {e}")
    
    # Se não encontrou questões, tenta um método ainda mais básico
    if not questions:
        logger.warning("Tentando método básico de parsing...")
        question_blocks = questions_text.split('\n\n')
        for block in question_blocks:
            if not block.strip():
                continue
                
            lines = block.strip().split('\n')
            first_line = lines[0].strip()
            q_match = re.match(r'Q(\d+)\.', first_line)
            
            if q_match:
                try:
                    q_num = int(q_match.group(1))
                    q_text = first_line[q_match.end():].strip()
                    
                    options = []
                    for line in lines[1:]:
                        line = line.strip()
                        if line.startswith(('A)', 'B)', 'C)', 'D)')):
                            options.append(line[3:].strip())
                    
                    if options:
                        questions.append(QuestionSchema(question_number=q_num, text=q_text, options=options))
                        logger.info(f"Método básico: Questão {q_num} com {len(options)} opções")
                except Exception as e:
                    logger.error(f"Erro no método básico: {e}")
    
    logger.info(f"Total de questões encontradas: {len(questions)}")
    
    exam_data = ExamDataSchema(metadata=metadata, questions=questions)

    # Parse Gabarito
    correct_answers = {}
    for line in gabarito_content.strip().split('\n'):
        match = re.match(r"Q(\d+):\s*([A-D])", line.strip())
        if match:
            correct_answers[int(match.group(1))] = match.group(2)
    
    logger.info(f"Gabarito processado com {len(correct_answers)} respostas")
    logger.info(f"Gabarito: {correct_answers}")

    return exam_data, correct_answers

# Carrega os dados na inicialização para evitar I/O repetido a cada request
parsed_exam_data, parsed_correct_answers = parse_exam_files()

def reload_exam_data():
    """Recarrega os dados da prova e do gabarito."""
    global parsed_exam_data, parsed_correct_answers
    logger.info("Recarregando dados da prova e gabarito...")
    parsed_exam_data, parsed_correct_answers = parse_exam_files()
    logger.info(f"Dados recarregados: {len(parsed_exam_data.questions)} questões, {len(parsed_correct_answers)} respostas")
    return parsed_exam_data, parsed_correct_answers
