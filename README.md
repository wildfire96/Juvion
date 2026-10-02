# Juvion

Estúdio de escrita para contos, romances e ficção, baseado no Writingway. O aplicativo usa Python 3.11 e PyQt5, com suporte previsto para Windows, Linux e macOS.

## Recursos

- Organização da obra em atos, capítulos e cenas, com versões nomeadas.
- Dois temas e modo foco com fundo personalizável.
- Universo com categorias, subcategorias, fichas opcionais, relações e linha do tempo.
- Assistência no manuscrito para reconhecer fichas e sugerir complementos do Universo.
- Mapa com imagem e marcadores vinculados às fichas.
- Modelos de obra, meta de palavras, progresso e revisão literária.
- Metadados de publicação e exportação DOCX, EPUB, PDF, HTML, Markdown e texto.
- Assistência opcional com provedores de IA configurados pelo usuário. O editor funciona sem contratar um provedor.

## Executar a partir do código

Use **Python 3.11**. Outras versões não são suportadas por esta configuração.

Windows: execute `setup_writingway.bat` uma vez e abra o aplicativo com `start.bat`. O nome antigo do script de instalação foi mantido para compatibilidade.

Linux/macOS: instale Python 3.11 e execute:

```sh
bash setup_writingway.sh
bash start.sh
```

Os scripts instalam as dependências em `venv`. A instalação a partir do código precisa de internet. Bibliotecas de sistema para Qt e o serviço de voz podem ser necessárias no Linux; a voz é opcional.

## Dados e backups

Na execução pelo código, os dados continuam no diretório do projeto. Faça backup de `Projects` e de `settings.json`; este último pode conter credenciais de provedores.

No executável, os dados ficam fora da pasta de instalação:

| Sistema | Pasta padrão |
| --- | --- |
| Windows | `%LOCALAPPDATA%/Juvion` |
| macOS | `~/Library/Application Support/Juvion` |
| Linux | `$XDG_DATA_HOME/juvion`, ou `~/.local/share/juvion` |

A variável opcional `JUVION_DATA_DIR` permite escolher outra pasta. Na primeira execução, dados de uma instalação antiga ao lado do executável são copiados, preservando os originais. Para trazer livros da versão de desenvolvimento, copie a pasta `Projects` para a pasta de dados do executável com o aplicativo fechado. As imagens novas de mapa são copiadas para a própria obra, permitindo mover o livro entre computadores.

## Gerar os pacotes

Cada pacote deve ser gerado no seu próprio sistema operacional. O PyInstaller não transforma um build Windows em um build Linux ou macOS.

- Windows: `build_windows.bat`. Produz uma pasta executável e ZIP; instale Inno Setup 6 para gerar também o instalador EXE.
- Linux: `bash build_linux.sh`. Produz um arquivo TAR.GZ e AppDir; `appimagetool` permite gerar AppImage.
- macOS: `bash build_macos.sh`. Produz APP e DMG.

O processo usa `package_app.py`, `juvion.spec` e a versão definida em `version.json`. Os pacotes contêm o Python e as dependências, portanto o usuário final não precisa instalá-los.

No macOS, a assinatura padrão é local (ad hoc). Para distribuição pública, configure `JUVION_CODESIGN_IDENTITY` com sua identidade de desenvolvedor e `JUVION_NOTARY_PROFILE` com um perfil de notarização previamente salvo no Keychain. Esses certificados e credenciais precisam ser fornecidos pelo responsável pela distribuição.

A configuração de build existe para as três plataformas. A aprovação de uma versão exige gerar os pacotes e conferir abertura, salvamento, reabertura, exportação e atualização em máquinas de cada sistema.

## Verificação

Com o ambiente ativado:

```sh
python -m compileall -q -x '(venv|\.venv|\.git|build|dist)[/\\]' .
python -m unittest discover -s tests -v
```

As verificações de regressão usam obras temporárias. O workflow de CI executa essas verificações nas três plataformas; o build dos pacotes pode ser solicitado manualmente.

## Licença e origem

O Juvion deriva do [Writingway](https://github.com/aomukai/Writingway), de aomukai. A licença Apache 2.0 escolhida para este repositório está em `LICENSE`. A licença MIT e o aviso de autoria original do Writingway são preservados em `LICENSE-Writingway`.
