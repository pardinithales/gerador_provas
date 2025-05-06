from pydantic import BaseModel
from typing import List, Dict, Optional

class QuestionSchema(BaseModel):
    question_number: int
    text: str
    options: List[str]

class ExamMetadataSchema(BaseModel):
    id: str
    titulo: str
    duracao_min: int

class ExamDataSchema(BaseModel):
    metadata: ExamMetadataSchema
    questions: List[QuestionSchema]

class AnswerSchema(BaseModel):
    question_number: int
    selected_option_index: int # Índice da opção selecionada (0=A, 1=B, ...)

class SubmissionSchema(BaseModel):
    student_identifier: str # Adicionado para identificar o aluno
    answers: List[AnswerSchema]

class ResultSchema(BaseModel):
    score: float
    correct_answers: int
    total_questions: int
    incorrect_questions: List[Dict] # {question_number, text, correct_answer_text, submitted_answer_text}

# Novos schemas para autenticação e atualização de conteúdo
class AdminLoginSchema(BaseModel):
    username: str
    password: str

class ContentUpdateSchema(BaseModel):
    exam_content: Optional[str] = None
    answers_content: Optional[str] = None
