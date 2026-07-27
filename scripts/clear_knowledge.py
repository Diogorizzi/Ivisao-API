import chromadb
from rich.console import Console
from rich.panel import Panel

console = Console()

def clear_rag_contents():
    # Rich header panel
    console.print(Panel.fit(
        "[bold yellow]Dartha RAG Cleaner - Limpador do Vector DB[/bold yellow]",
        border_style="yellow"
    ))

    try:
        chroma_client = chromadb.HttpClient(host="localhost", port=8000)
        console.print("[+] Conectado ao ChromaDB via HTTP no Docker (localhost:8000)", style="cyan")
    except Exception as e:
        console.print("[-] Falhou em conectar ao Chroma Server, tentando modo Local persistente...", style="yellow")
        chroma_client = chromadb.PersistentClient(path="./chroma_data")

    try:
        chroma_client.delete_collection("dartha_knowledge")
        console.print("[+] [bold green]SUCESSO:[/bold green] Todos os registros da base de conhecimento 'dartha_knowledge' foram apagados.", style="green")
    except Exception as e:
        console.print(f"[-] A coleção não foi encontrada ou já está vazia. (Detalhe: {e})", style="yellow")

    console.print("\n[dim]Você já pode adicionar novos arquivos na pasta 'data/RAG' e rodar 'python scripts/ingest_knowledge.py' para reindexar.[/dim]")

if __name__ == "__main__":
    clear_rag_contents()
