Packaging et publication

But: décrire comment builder et publier sur TestPyPI / PyPI, checklist CI et fichiers à inclure/exclure.

Étapes rapides

1. Build localement

```bash
python -m pip install --upgrade build twine
python -m build
```

2. Tester l'installation

```bash
python -m pip install dist/*
python -c "import taskmajor; print(taskmajor.__name__)"
```

3. Publier sur TestPyPI

```bash
python -m pip install --upgrade twine
python -m twine upload --repository testpypi dist/*
```

Notes

- Les profiles et fichiers de config par défaut sont inclus via MANIFEST.in et l'option hatch build.include.
- Ne pas emballer les données utilisateur (~/.taskrc, ~/.task) ; documenter les chemins par défaut et variables d'environnement pour les overrides.
