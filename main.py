from src.ingestion.demonstracoes_contabeis import DemonstracoesContabeisIngestor

obj = DemonstracoesContabeisIngestor(start_year=2020, end_year=None)
start_year = obj.start_year
end_year = obj.end_year
print(f"Start Year: {start_year}, End Year: {end_year}")