import os
import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import load_dotenv

from app.schemas.exam import ResultSchema

# Configuração de logging mais detalhada
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente do .env.local
load_dotenv(dotenv_path=".env.local")
logger.info("Carregando variáveis de ambiente de .env.local")

# Configuração do Jinja2 para carregar templates da pasta 'app/templates'
env = Environment(
    loader=FileSystemLoader("app/templates"),
    autoescape=select_autoescape(['html', 'xml'])
)

# Configurações de SMTP (do .env.local)
SMTP_HOSTNAME = os.getenv("SMTP_HOSTNAME")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

# Log das configurações SMTP (sem a senha)
logger.info(f"Configuração SMTP: Host={SMTP_HOSTNAME}, Port={SMTP_PORT}, User={SMTP_USERNAME}, From={SMTP_FROM_EMAIL}, Admin={ADMIN_EMAIL}")

async def send_email(to_email: str, subject: str, html_content: str):
    """Envia um e-mail de forma assíncrona."""
    logger.info(f"Tentando enviar e-mail para {to_email} com assunto: {subject}")
    
    if not all([SMTP_HOSTNAME, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL]):
        logger.error("Configurações SMTP incompletas no .env.local. E-mail não enviado.")
        logger.error(f"Valores: HOSTNAME={SMTP_HOSTNAME}, USERNAME={SMTP_USERNAME}, PASSWORD={'*'*8 if SMTP_PASSWORD else 'None'}, FROM={SMTP_FROM_EMAIL}")
        return

    message = MIMEMultipart("alternative")
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = subject

    # Anexa a parte HTML
    message.attach(MIMEText(html_content, "html"))

    try:
        logger.debug(f"Conectando ao servidor SMTP {SMTP_HOSTNAME}:{SMTP_PORT}")
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOSTNAME,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            start_tls=True # Ou use use_tls=True se a porta for 465
        )
        logger.info(f"E-mail enviado com sucesso para {to_email}")
    except aiosmtplib.SMTPException as e:
        logger.error(f"Falha ao enviar e-mail para {to_email}: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao enviar e-mail para {to_email}: {e}")
        import traceback
        logger.error(traceback.format_exc())

async def send_results_emails(student_identifier: str, result: ResultSchema, exam_title: str, timestamp: str):
    """Renderiza os templates e envia os e-mails para o aluno e o admin."""
    logger.info(f"Preparando e-mails para {student_identifier} - {exam_title}")

    # Renderiza e-mail para o aluno
    try:
        template_aluno = env.get_template("email_aluno.html")
        html_aluno = template_aluno.render(
            exam_title=exam_title,
            student_identifier=student_identifier,
            result=result,
            timestamp=timestamp
        )
        # Assume que o student_identifier é o email do aluno
        await send_email(student_identifier, f"Resultado da Prova: {exam_title}", html_aluno)
    except Exception as e:
        logger.error(f"Erro ao renderizar ou enviar e-mail para o aluno {student_identifier}: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Renderiza e-mail para o admin
    if ADMIN_EMAIL:
        try:
            template_admin = env.get_template("email_admin.html")
            html_admin = template_admin.render(
                exam_title=exam_title,
                student_identifier=student_identifier,
                result=result,
                timestamp=timestamp
            )
            await send_email(ADMIN_EMAIL, f"Submissão de Prova: {student_identifier} - {exam_title}", html_admin)
        except Exception as e:
            logger.error(f"Erro ao renderizar ou enviar e-mail para o admin {ADMIN_EMAIL}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        logger.warning("ADMIN_EMAIL não definido no .env.local. E-mail do admin não enviado.")
