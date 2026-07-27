import io
import logging
import pandas as pd
from docx import Document

logger = logging.getLogger(__name__)

def parse_document_to_markdown(file_bytes: bytes, filename: str) -> str:
    """
    Extrai o texto/dados do arquivo anexado e converte para Markdown.
    Apoiado por python-docx e pandas (para suporte a xlsx/csv on-the-fly).
    O resultado deve ser anexado ao prompt da LLM.
    """
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    
    try:
        if ext == 'docx':
            logger.info(f"Parsing DOCX in-memory: {filename}")
            doc = Document(io.BytesIO(file_bytes))
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            text = "\n\n".join(paragraphs)
            return f"\n<file_attachment name=\"{filename}\">\n{text}\n</file_attachment>"
            
        elif ext == 'csv':
            logger.info(f"Parsing CSV in-memory: {filename}")
            # Tenta decodificar o CSV usando utf-8 ou latin1 caso falhe
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding='latin1')
            
            # Limita a 500 linhas para não estourar tokens caso não seja necessário ler lixo da planilha
            if len(df) > 500:
                logger.warning(f"Planilha CSV muito grande, processando apenas as primeiras 500 linhas.")
                df = df.head(500)
                
            md_table = df.to_markdown(index=False)
            return f"\n<file_attachment name=\"{filename}\">\n{md_table}\n</file_attachment>"
            
        elif ext in ['xlsx', 'xls']:
            logger.info(f"Parsing Excel in-memory: {filename}")
            try:
                engine = 'openpyxl' if ext == 'xlsx' else None
                dfs = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None, engine=engine)
            except Exception as read_err:
                # Se falhar tenta de novo sem engine forçado
                logger.warning(f"Engine openpyxl falhou ou arquivo é CSV fake. {read_err}")
                dfs = {"Planilha1": pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python')}
                
            md_tables = []
            for sheet_name, df in dfs.items():
                if len(df) > 500:
                    df = df.head(500)
                md_table = df.to_markdown(index=False)
                md_tables.append(f"### Aba (Sheet): {sheet_name}\n{md_table}")
                
            return f"\n<file_attachment name=\"{filename}\">\n" + "\n\n".join(md_tables) + "\n</file_attachment>"
            
        else:
            logger.warning(f"Extensão não contemplada pelo parser in-memory: {ext}")
            return ""
            
    except Exception as e:
        logger.error(f"Erro ao converter o documento {filename}: {str(e)}")
        return f"[Sistema detectou um erro ou formato corrompido ao ler {filename}. Diga ao usuário que não foi possível extrair o texto completo.]"
