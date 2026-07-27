"""
SmartPandasTools: Versão defensiva do PandasTools que intercepta erros comuns da LLM.

Problemas que resolve:
1. LLM usa read_csv em arquivo .xlsx → auto-corrige para read_excel + openpyxl
2. LLM esquece engine='openpyxl' → adiciona automaticamente
3. LLM usa filepath_or_buffer ao invés de io para read_excel → normaliza
4. LLM esquece operation_parameters em run_dataframe_operation → default {}
5. LLM tenta operar em dataframe inexistente → mensagem clara
6. CSV com encoding errado → tenta múltiplos encodings automaticamente
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from agno.tools import Toolkit
from agno.utils.log import log_debug, logger

try:
    import pandas as pd
except ImportError:
    raise ImportError("`pandas` not installed. Please install using `pip install pandas`.")


class SmartPandasTools(Toolkit):
    def __init__(
        self,
        enable_create_pandas_dataframe: bool = True,
        enable_run_dataframe_operation: bool = True,
        all: bool = False,
        **kwargs,
    ):
        self.dataframes: Dict[str, pd.DataFrame] = {}

        tools: List[Any] = []
        if all or enable_create_pandas_dataframe:
            tools.append(self.create_pandas_dataframe)
        if all or enable_run_dataframe_operation:
            tools.append(self.run_dataframe_operation)

        super().__init__(name="pandas_tools", tools=tools, **kwargs)

    def _detect_file_path(self, function_parameters: Dict[str, Any]) -> Optional[str]:
        """Extrai o caminho do arquivo dos parâmetros, independente do nome do parâmetro usado."""
        for key in ("io", "filepath_or_buffer", "path_or_buf", "path"):
            val = function_parameters.get(key)
            if val and isinstance(val, str):
                return val
        return None

    def _auto_correct_for_excel(
        self, file_path: str, create_using_function: str, function_parameters: Dict[str, Any]
    ) -> tuple:
        """Auto-corrige parâmetros quando detecta um arquivo Excel."""
        path_lower = file_path.lower()

        if ".xlsx" in path_lower or (path_lower.endswith(".xls") and ".xls" in path_lower):
            # Força read_excel, independente do que a LLM pediu
            if create_using_function != "read_excel":
                logger.info(f"[SmartPandas] Auto-corrigido {create_using_function} -> read_excel para: {file_path}")
            create_using_function = "read_excel"

            # Normaliza parâmetros: remove nomes errados, usa 'io'
            clean_params = {
                k: v for k, v in function_parameters.items()
                if k not in ("filepath_or_buffer", "path_or_buf", "path")
            }
            clean_params["io"] = file_path
            clean_params.setdefault("engine", "openpyxl")
            function_parameters = clean_params

        return create_using_function, function_parameters

    def create_pandas_dataframe(
        self, dataframe_name: str, create_using_function: str, function_parameters: Dict[str, Any]
    ) -> str:
        """Creates a pandas dataframe named `dataframe_name` by running a function `create_using_function` with the parameters `function_parameters`.
        Returns the created dataframe name as a string if successful, otherwise returns an error message.

        IMPORTANT FOR EXCEL FILES:
        - Use create_using_function='read_excel' with function_parameters={'io': 'path/to/file.xlsx', 'engine': 'openpyxl'}
        - Do NOT use read_csv for .xlsx files

        For Example:
        - Excel: {"dataframe_name": "df", "create_using_function": "read_excel", "function_parameters": {"io": "data.xlsx", "engine": "openpyxl"}}
        - CSV: {"dataframe_name": "df", "create_using_function": "read_csv", "function_parameters": {"filepath_or_buffer": "data.csv"}}

        :param dataframe_name: The name of the dataframe to create.
        :param create_using_function: The function to use to create the dataframe.
        :param function_parameters: The parameters to pass to the function.
        :return: The name of the created dataframe if successful, otherwise an error message.
        """
        try:
            log_debug(f"Creating dataframe: {dataframe_name}")
            log_debug(f"Using function: {create_using_function}")
            log_debug(f"With parameters: {function_parameters}")

            if dataframe_name in self.dataframes:
                return f"Dataframe already exists: {dataframe_name}"

            # Auto-detecta e corrige o tipo de arquivo
            file_path = self._detect_file_path(function_parameters)
            if file_path:
                create_using_function, function_parameters = self._auto_correct_for_excel(
                    file_path, create_using_function, function_parameters
                )

            # Para CSV, tenta múltiplos encodings
            if create_using_function == "read_csv":
                df = self._read_csv_with_fallback(function_parameters)
            else:
                df = getattr(pd, create_using_function)(**function_parameters)

            if df is None:
                return f"Error creating dataframe: result is None for '{dataframe_name}'"
            if not isinstance(df, pd.DataFrame):
                return f"Error creating dataframe: result is not a DataFrame for '{dataframe_name}'"
            if df.empty:
                return f"Dataframe is empty: {dataframe_name}"

            self.dataframes[dataframe_name] = df
            row_count = len(df)
            col_names = list(df.columns)
            logger.info(f"[SmartPandas] Dataframe '{dataframe_name}' criado: {row_count} linhas, colunas: {col_names}")
            return f"{dataframe_name} (criado com sucesso: {row_count} linhas, colunas: {col_names})"
        except Exception as e:
            logger.error(f"Error creating dataframe: {e}")
            return f"Error creating dataframe: {e}"

    def _read_csv_with_fallback(self, function_parameters: Dict[str, Any]) -> pd.DataFrame:
        """Tenta ler CSV com múltiplos encodings."""
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        last_error = None

        for enc in encodings:
            try:
                params = {**function_parameters, "encoding": enc}
                df = pd.read_csv(**params)
                logger.info(f"[SmartPandas] CSV lido com encoding '{enc}'")
                return df
            except UnicodeDecodeError as e:
                last_error = e
                continue
            except Exception as e:
                # Se não for erro de encoding, propaga
                raise e

        raise last_error or Exception("Failed to read CSV with any encoding")

    def run_dataframe_operation(
        self, dataframe_name: str, operation: str, operation_parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Runs an operation `operation` on a dataframe `dataframe_name` with the parameters `operation_parameters`.
        Returns the result of the operation as a string if successful, otherwise returns an error message.

        IMPORTANT: operation_parameters is optional. Use {} or omit it for operations without arguments.

        For Example:
        - Get first 10 rows: {"dataframe_name": "df", "operation": "head", "operation_parameters": {"n": 10}}
        - Get shape: {"dataframe_name": "df", "operation": "shape", "operation_parameters": {}}
        - Get description: {"dataframe_name": "df", "operation": "describe", "operation_parameters": {}}
        - Filter rows: {"dataframe_name": "df", "operation": "query", "operation_parameters": {"expr": "column_name == 'value'"}}
        - Value counts: {"dataframe_name": "df", "operation": "value_counts", "operation_parameters": {"subset": ["column_name"]}}

        :param dataframe_name: The name of the dataframe to run the operation on.
        :param operation: The operation to run on the dataframe.
        :param operation_parameters: Optional parameters for the operation (defaults to {}).
        :return: The result of the operation if successful, otherwise an error message.
        """
        if operation_parameters is None:
            operation_parameters = {}

        try:
            log_debug(f"Running operation: {operation}")
            log_debug(f"On dataframe: {dataframe_name}")
            log_debug(f"With parameters: {operation_parameters}")

            dataframe = self.dataframes.get(dataframe_name)
            if dataframe is None:
                available = list(self.dataframes.keys())
                return (
                    f"Error: Dataframe '{dataframe_name}' não encontrado. "
                    f"Dataframes disponíveis: {available}. "
                    f"Crie o dataframe primeiro usando create_pandas_dataframe."
                )

            attr = getattr(dataframe, operation, None)
            if attr is None:
                return f"Error: Operação '{operation}' não existe no DataFrame. Operações comuns: head, tail, describe, shape, columns, query, value_counts, groupby, info"

            # Distinguir propriedades (shape, columns, dtypes) de métodos (head, tail, etc)
            if callable(attr):
                result = attr(**operation_parameters)
            else:
                result = attr  # Propriedades como .shape, .columns, .dtypes

            log_debug(f"Ran operation: {operation}")
            try:
                try:
                    return result.to_string()
                except AttributeError:
                    return str(result)
            except Exception:
                return "Operation ran successfully"
        except Exception as e:
            logger.error(f"Error running operation: {e}")
            return f"Error running operation: {e}"
