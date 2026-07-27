"""
Valida configuração antes do startup.

Uso:
    python scripts/validate_config.py
"""
from pathlib import Path
from rich.console import Console
from rich.table import Table

from src.agents._config import load_system_config

console = Console()


def validate_config():
    """Valida configuração completa do sistema"""
    console.print("[bold blue]🔍 Validando Configuração[/bold blue]\n")

    errors = []
    warnings = []

    try:
        # Carrega config
        config = load_system_config()

        console.print(f"[green]✓[/green] Empresa: {config.company.company_name}")
        console.print(f"[green]✓[/green] Modelo padrão: {config.company.default_model}")
        console.print(f"[green]✓[/green] Agentes carregados: {len(config.agents)}\n")

        # Tabela de agentes
        table = Table(title="Agentes Configurados")
        table.add_column("Nome", style="cyan")
        table.add_column("Departamento", style="yellow")
        table.add_column("Modelo", style="green")
        table.add_column("RAG", justify="center")
        table.add_column("Tools", justify="right")
        table.add_column("Skills", justify="right")

        for agent in config.agents:
            table.add_row(
                agent.name,
                agent.department or "ADMIN",
                agent.model or config.company.default_model,
                "✓" if agent.features.rag else "✗",
                str(len(agent.tools)),
                str(len(agent.skills))
            )

        console.print(table)

        # Validações específicas
        for agent in config.agents:
            # Verifica se departamento existe
            if agent.features.rag and agent.department:
                dept_path = Path(f"data/{agent.department}")
                if not dept_path.exists():
                    warnings.append(
                        f"Agente '{agent.name}': departamento '{agent.department}' "
                        f"não existe em data/"
                    )

            # Verifica skills duplicadas
            if len(agent.skills) != len(set(agent.skills)):
                warnings.append(f"Agente '{agent.name}': skills duplicadas")

        # Imprime warnings
        if warnings:
            console.print("\n[bold yellow]⚠ Avisos:[/bold yellow]")
            for warn in warnings:
                console.print(f"  • {warn}")

        # Sucesso
        if not errors:
            console.print("\n[bold green]✅ Configuração válida![/bold green]")
            return True

    except Exception as e:
        console.print(f"\n[bold red]✗ Erro na validação:[/bold red]")
        console.print(f"  {str(e)}")
        return False


if __name__ == "__main__":
    success = validate_config()
    exit(0 if success else 1)
