import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const python=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
if(!existsSync(python)) {console.error('Set up the backend first: python -m venv .venv, then install backend/requirements.txt with the virtual environment Python. See README.md.');process.exit(1);}
const children=[];let stopping=false;
function stop(code=0){if(stopping)return;stopping=true;for(const child of children)child.kill();process.exitCode=code;}
function start(command,args){const child=spawn(command,args,{cwd:root,stdio:'inherit',windowsHide:true});children.push(child);child.on('error',error=>{console.error(error.message);stop(1)});child.on('exit',code=>{if(!stopping)stop(code||0)});}
start(python,['-X','utf8','backend/server.py']);
start(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173','--strictPort']);
process.on('SIGINT',()=>stop());process.on('SIGTERM',()=>stop());
