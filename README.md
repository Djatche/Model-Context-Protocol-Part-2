# Mon premier MCP (Model Context Protocol) - Part 2.


Pour cette deuxième partie de l’article, nous avons intégré un llm en l’occurrence llama3.2

c’est un llm que l’on peut exécuter en local de façon sécurisé et sans frais en local.

Pour cette intégration nous avons rajouté 2 fonctions dans le fichier mcp\_client.py :

    - get\_context \_form \_mc p

Elle permet de récupérer un contexte qui est une concaténation de la ressource (issu du fichier txt) et du prompt

    - call\_llama\_llm\_with context

Elle permet d’appeler le llm en y introduisant le contexte issu de la précédente fonction



