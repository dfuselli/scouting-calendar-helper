shortcut_categorie = {
    "Giovanissimi": "Giov.",
    "Esordienti": "Esord.",
    "Pulcini": "Pulc.",
    "MiniPulcini": "MiniPulc.",
}

def merge_categoria_federazione(categoria):
    if categoria:
        compressed = ""
        for word in categoria.split(" "):
            if word in shortcut_categorie:
                compressed += shortcut_categorie[word]
            else:
                compressed += word
            compressed += " "  # aggiunge spazio tra le parole
        return compressed.strip()  # rimuove spazio finale
    return categoria