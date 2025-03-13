from spellchecker import SpellChecker

# Configure o corretor para português
spell = SpellChecker(language='pt')

def correct_text(text: str) -> str:
    """
    Corrige erros ortográficos simples na string de entrada.
    Essa função divide o texto em palavras, corrige cada palavra (se for considerado mal escrito)
    e reconstrói a frase.
    """
    words = text.split()
    corrected_words = []
    for word in words:
        # Se a palavra é numérica ou muito curta, mantém como está
        if word.isdigit() or len(word) < 3:
            corrected_words.append(word)
        else:
            # Corrige a palavra; se não houver sugestão, mantém a original
            corrected = spell.correction(word)
            corrected_words.append(corrected if corrected else word)
    return " ".join(corrected_words)
