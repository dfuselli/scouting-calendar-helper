shortcut_categorie = {
    "ALLIEVI": "Allievi",
    "GIOVANISSIMI": "Giov.",
    "ESORDIENTI": "Esord.",
    "PULCINI": "Pulc.",
    "PRIMICALCI": "PrimiCalci",
    "PICCOLIAMICI": "PiccAmici",
    "MINIPULCINI": "MiniPulc.",
}


def merge_categoria_federazione(categoria):
    if categoria:
        compressed = ""
        for word in categoria.split(" "):
            if not word:  # salta parole vuote
                continue
            if word.upper() in shortcut_categorie:
                compressed += shortcut_categorie[word.upper()]
            else:
                compressed += " " + word
        return compressed.strip()  # rimuove spazio finale
    return categoria
