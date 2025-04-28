from .services.zapi import enviar_mensagem, enviar_midia

def notificar_usuario(usuario):
    numero = usuario.telefone  # Ex: 5511999999999
    mensagem = f"Olá {usuario.nome}, sua cobrança foi gerada com sucesso!"
    resposta = enviar_mensagem(numero, mensagem)
    print(resposta)

def enviar_pdf(usuario, url_pdf):
    legenda = f"Olá {usuario.nome}, aqui está seu comprovante."
    return enviar_midia(usuario.telefone, url_pdf, legenda)
