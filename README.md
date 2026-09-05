# Reprodução Local da Página Vakinha: "Força, Kabuto"

Clone de altíssima fidelidade visual e interativa da página da campanha Vakinha:
**URL Original:** `https://www.vakinha.com.br/vaquinha/forca-kabuto-juntos-pela-sua-recuperacao?utm_internal_source=home_most_loved`

---

## 🚀 Como Executar o Projeto

Para iniciar o servidor local, execute no terminal (na pasta do projeto):

```powershell
python server.py
```

Ou, utilizando o módulo nativo do Python:

```powershell
python -m http.server 3000
```

Abra no seu navegador:
👉 **[http://localhost:3000](http://localhost:3000)**

---

## 📁 Estrutura do Projeto

```
vakinha-clone/
├── index.html                  # Estrutura completa da página e marcação semântica
├── assets/
│   ├── css/
│   │   ├── main.css            # 124KB de estilos originais (styled-components + Next.js)
│   │   └── interactions.css    # Animações, modais, drawer mobile, abas e toasts
│   ├── js/
│   │   └── main.js             # Lógica interativa (PIX, abas, modal, coração, drawer)
│   └── images/
│       ├── kabuto.jpg          # Foto principal da campanha
│       ├── selo.png            # Selo oficial Vakinha
│       └── favicon.ico         # Favicon original
├── server.py                   # Servidor HTTP local configurado na porta 3000
└── README.md                   # Esta documentação
```

---

## 🎨 Componentes Reproduzidos com Máxima Fidelidade

1. **Header Fixo (Sticky / Elevation)**:
   - Logo oficial Vakinha em SVG verde `#24CA68`.
   - **Desktop**: Menus dropdown interativos ("Doar", "Arrecadar", "Sobre"), busca, minha conta e botão "Faz uma vaquinha!".
   - **Mobile**: Menu hambúrguer com gaveta animada lateral (`drawer`) e overlay escuro.
2. **Coluna Esquerda da Campanha**:
   - Imagem de capa com proporção fiel e botão flutuante interativo de coração (`heRobj`).
   - Tag de categoria `SAÚDE / TRATAMENTOS`, título `h1` em Montserrat Bold 32px e ID `6290503`.
   - Texto de introdução com expansão suave ("ver tudo" / "ver menos").
   - Barra de selos oficiais recebidos pela comunidade com PNGs autênticos.
   - **Navegação em Abas**:
     - **Sobre**: Data de criação e texto completo do relato da campanha com ícones vetoriais modernos.
     - **Quem ajudou**: Lista dos 9.720 apoiadores com valores e doadores recentes.
     - **Vakinha Premiada**: Explicação das chances e números da sorte da Loteria Federal.
     - **Selos recebidos**: Grade com as conquistas oficiais da campanha em PNG autêntico com alta resolução.
     - **Perguntas e Respostas**: Acordeão interativo com as principais dúvidas sobre a campanha.
   - Link de denúncia e aviso legal oficial da Vakinha.
3. **Sidebar Direita (Sticky Card)**:
   - Card fixo ao rolar a página (`top: 15px`).
   - Barra de progresso verde (`#24CA68`) 100% preenchida (meta superada: R$ 728.742,37 de R$ 650.000,00).
   - Card verde claro (`#EEFFE6`) com total de corações (9340) e apoiadores (9720).
   - Botão verde "Quero Ajudar" (abre simulador de doação com opções de valores e PIX).
   - Botão outline "Compartilhar" (abre modal com WhatsApp, Facebook e Copiar link).
   - Selo oficial em SVG "Doador Protegido".
   - Card da criadora "Fernanda Mayumi Machado Masuda" com status "Ativo(a) desde agosto/2026".
4. **Seção de Campanhas Recomendadas**:
   - "Outras histórias também precisam de você!" com cards estilizados e responsivos.
5. **Footer Completo**:
   - Background escuro `#282828`, logo branca da Vakinha em SVG, redes sociais com ícones originais, 4 colunas de links institucionais, selo do Reclame Aqui e dados fiscais/CNPJ.

---

## 📱 Responsividade Testada

- **1920px / 1440px / 1366px**: Layout widescreen com container centralizado de 1140px, coluna dupla e sidebar sticky.
- **1024px**: Layout intermediário com proporções fluidas.
- **768px**: Ponto de quebra onde a coluna lateral se posiciona abaixo da principal e o header se adapta ao padrão mobile.
- **430px / 390px / 375px**: Layout mobile otimizado, abas com rolagem horizontal, botões full-width e drawer lateral.
