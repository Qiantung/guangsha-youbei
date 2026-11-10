import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import timedelta
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def call(tool='get_weekly_features',dataset_id='demo_01',start_date=None,end_date=None):
    parameters=StdioServerParameters(command=sys.executable,args=['-m','wearable.server'],env=dict(os.environ),cwd=str(Path(__file__).resolve().parents[1]))
    arguments={'dataset_id':dataset_id}
    if start_date is not None: arguments['start_date']=start_date
    if end_date is not None: arguments['end_date']=end_date
    async with stdio_client(parameters) as (read,write):
        async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=30)) as session:
            initialized=await session.initialize()
            tools=await session.list_tools()
            result=await session.call_tool(tool,arguments=arguments)
            payload=result.structuredContent
            if payload is None: payload=json.loads(result.content[0].text)
            return {'transport':'stdio','initialized':True,'protocol_version':initialized.protocolVersion,
                'tools':[t.name for t in tools.tools],'tool':tool,'arguments':arguments,'result':payload}

if __name__=='__main__':
    print(json.dumps(asyncio.run(call()),ensure_ascii=False,allow_nan=False,indent=2))
