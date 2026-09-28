"""Image observation through subscription-authenticated Codex/Claude CLIs only."""
from __future__ import annotations
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def subscription_env():
    env=dict(os.environ)
    for key in list(env):
        if (key.endswith('_API_KEY') or key in ('ANTHROPIC_AUTH_TOKEN','ANTHROPIC_BASE_URL','OPENAI_BASE_URL',
            'CLAUDE_CODE_OAUTH_TOKEN','CLAUDECODE','CLAUDE_CODE_USE_BEDROCK','CLAUDE_CODE_USE_VERTEX','CLAUDE_CODE_USE_FOUNDRY')):
            env.pop(key,None)
    return env


def observe_subscription(data,mime,prompt,*,provider,model,archive_dir):
    if provider not in ('codex','claude'):raise ValueError('Unsupported subscription observer')
    binary=shutil.which(provider)
    if not binary:raise RuntimeError('Observer CLI unavailable')
    env=subscription_env()
    authcmd=[binary,'login','status'] if provider=='codex' else [binary,'auth','status']
    auth=subprocess.run(authcmd,capture_output=True,text=True,env=env,timeout=15)
    if provider=='codex':
        authenticated=auth.returncode==0 and 'logged in using chatgpt' in (auth.stdout+auth.stderr).lower()
    else:
        try:
            status=json.loads(auth.stdout)
            authenticated=(auth.returncode==0 and status.get('loggedIn') is True and status.get('authMethod')=='claude.ai' and status.get('apiProvider')=='firstParty')
        except (ValueError,TypeError):authenticated=False
    if not authenticated:raise RuntimeError('Subscription login required; API fallback disabled')
    # Preserve image inputs; only temporary text/schema files are removed.
    archive=Path(archive_dir);archive.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(data).hexdigest()
    suffix={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}[mime]
    image_path=(archive/(digest+suffix)).resolve()
    if not image_path.exists():image_path.write_bytes(data)
    with tempfile.TemporaryDirectory(prefix='kairos-observe-') as temp:
        work=Path(temp);output=work/'result.json'
        if provider=='codex':
            schema=work/'schema.json';schema.write_text(json.dumps({'type':'object','properties':{'observation':{'type':'string'}},'required':['observation'],'additionalProperties':False}))
            cmd=[binary,'exec','--ignore-user-config','--ephemeral','--skip-git-repo-check',
                 '-s','read-only','-c','approval_policy="never"','-c','model_provider="openai"',
                 '-c','model_reasoning_effort="low"','-m',model,'--json','--output-schema',str(schema),
                 '-o',str(output),prompt,'-i',str(image_path)]
            result=subprocess.run(cmd,capture_output=True,text=True,cwd=work,env=env,timeout=120)
            if result.returncode!=0 or not output.exists():raise RuntimeError('Codex observation failed')
            value=json.loads(output.read_text());usage={}
            for line in result.stdout.splitlines():
                try:event=json.loads(line)
                except ValueError:continue
                if event.get('type')=='turn.completed':usage=event.get('usage',{})
            reported=None
        else:
            message={'type':'user','message':{'role':'user','content':[
                {'type':'image','source':{'type':'base64','media_type':mime,'data':base64.b64encode(data).decode()}},
                {'type':'text','text':prompt}]}}
            cmd=[binary,'--safe-mode','--print','--model',model,'--effort','low',
                 '--input-format','stream-json','--output-format','stream-json','--verbose','--tools','',
                 '--strict-mcp-config','--mcp-config','{"mcpServers":{}}',
                 '--disable-slash-commands','--no-session-persistence','--max-turns','1']
            result=subprocess.run(cmd,input=json.dumps(message)+'\n',capture_output=True,text=True,cwd=work,env=env,timeout=120)
            if result.returncode!=0:raise RuntimeError('Claude observation failed')
            events=[json.loads(line) for line in result.stdout.splitlines() if line.strip()]
            outer=next((event for event in reversed(events) if event.get('type')=='result'),None)
            if outer is None:raise RuntimeError('Claude result missing')
            if outer.get('is_error'):raise RuntimeError('Claude observation failed')
            raw=outer.get('result','').strip()
            if raw.startswith('```'):raw='\n'.join(raw.splitlines()[1:-1])
            value=json.loads(raw);usage=outer.get('usage',{});reported=outer.get('total_cost_usd')
    text=value.get('observation')
    if not isinstance(text,str) or not text.strip() or len(text)>1600:raise ValueError('Invalid observation')
    value['usage']={'provider':provider,'model_requested':model,'auth_route':'subscription_cli',
                    'tokens':usage,'cli_reported_cost_usd':reported,
                    'billing_note':'CLI usage report is not an additional API invoice; subscription allowance consumed'}
    return value
