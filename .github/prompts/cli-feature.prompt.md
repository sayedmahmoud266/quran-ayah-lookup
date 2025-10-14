---
mode: agent
---

# Role
You are a highly skilled software developer specialized in python applications.


# Task
Your task is to add a cli feature to the existing python package.
The cli feature should allow users to interact with the package via command line interface.
The newly added cli feature should NOT break or update any existing functionality of the package.


# Acceptance Criteria
1. The new cli feature should be accessible via a command line command named `quran-ayah-lookup` or `qal` for short.
2. The cli should provide a help option that lists all available commands and their descriptions.
3. The cli should basically map all exposed functions of the package to corresponding cli commands.
4. The cli should default into a repl mode if no command is provided.
5. The cli should provide meaningful error messages for invalid commands or arguments.

# Notes
- Ensure to read documentation of the existing package to understand its structure and functionality.
- Use any appropriate libraries or frameworks to implement the cli feature.
- Write clean, maintainable, and well-documented code.
- Include unit tests to verify the functionality of the cli feature.
- Update the readme file to include instructions on how to use the new cli feature.
- Ensure to follow best practices for python development and cli design.
