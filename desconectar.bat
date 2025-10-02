@echo off
rem Este comando busca tu sesin de usuario actual y la conecta a la consola, 
rem dejando el escritorio activo despus de que te desconectes.
for /f "skip=1 tokens=3" %%s in ('query user %USERNAME%') do (tscon %%s /dest:console)
