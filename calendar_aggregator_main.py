import pandas as pd
import os

def normalize_text(value):
    """Normalizza il testo rendendolo capitalizzato correttamente."""
    if isinstance(value, str):
        # Rimuove spazi extra e capitalizza ogni parola
        return ' '.join(word.capitalize() for word in value.strip().split())
    return value

def merge_excel_sheets(input_file: str, output_file: str):
    """
    Legge tutti i fogli di un file Excel e li unisce in un unico DataFrame.
    Normalizza le stringhe e salva il risultato in un nuovo Excel.
    """
    # Legge tutti i fogli
    all_sheets = pd.read_excel(input_file, sheet_name=None)

    # Concatena tutti i DataFrame
    combined_df = pd.concat(all_sheets.values(), ignore_index=True)

    # Normalizza il testo colonna per colonna
    for col in combined_df.columns:
        combined_df[col] = combined_df[col].apply(normalize_text)

    # Scrive il risultato in un nuovo file Excel
    combined_df.to_excel(output_file, index=False)

    print(f"✅ File unificato creato con successo: {output_file}")


def main():
    input_path = "app/resources/AllCalendars.xlsx"   # <-- metti qui il nome del file di input
    output_path = "app/resources/AllCalendarsUnified.xlsx"

    if not os.path.exists(input_path):
        print(f"❌ File non trovato: {input_path}")
        return

    merge_excel_sheets(input_path, output_path)


if __name__ == "__main__":
    main()
