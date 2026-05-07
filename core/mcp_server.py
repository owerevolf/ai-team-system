"""
MCP (Model Context Protocol) Server Support
Позволяет агентам использовать внешние MCP-серверы как инструменты.

Поддерживает:
- stdio транспорт (запуск MCP серверов как подпроцессов)
- HTTP транспорт (подключение к удалённым MCP серверам)
- Авто-обнаружение инструментов с MCP серверов
"""

import os
import json
import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger


@dataclass
class MCPServerConfig:
    """Конфигурация MCP сервера"""
    name: str
    command: str  # команда для запуска (stdio) или URL (HTTP)
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"  # "stdio" или "http"
    enabled: bool = True


@dataclass
class MCPTool:
    """Инструмент с MCP сервера"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


class MCPServer:
    """Подключение к одному MCP серверу"""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.tools: Dict[str, MCPTool] = {}
        self._connected = False
    
    async def connect(self):
        """Подключение к MCP серверу"""
        if self.config.transport == "stdio":
            await self._connect_stdio()
        elif self.config.transport == "http":
            await self._connect_http()
        self._connected = True
        logger.info(f"MCP server '{self.config.name}' connected, {len(self.tools)} tools")
    
    async def _connect_stdio(self):
        """Подключение через stdio"""
        try:
            cmd = [self.config.command] + self.config.args
            env = {**os.environ, **self.config.env}
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )
            
            # Отправляем initialize
            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "ai-team-system", "version": "2.1.0"}
                }
            }
            self.process.stdin.write(json.dumps(init_msg) + "\n")
            self.process.stdin.flush()
            
            # Читаем ответ
            response = self.process.stdout.readline()
            if response:
                data = json.loads(response)
                logger.debug(f"MCP init response: {data}")
            
            # Запрашиваем список инструментов
            tools_msg = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            self.process.stdin.write(json.dumps(tools_msg) + "\n")
            self.process.stdin.flush()
            
            response = self.process.stdout.readline()
            if response:
                data = json.loads(response)
                tools = data.get("result", {}).get("tools", [])
                for tool in tools:
                    self.tools[tool["name"]] = MCPTool(
                        name=tool["name"],
                        description=tool.get("description", ""),
                        input_schema=tool.get("inputSchema", {}),
                        server_name=self.config.name
                    )
                    
        except Exception as e:
            logger.error(f"MCP server '{self.config.name}' connection failed: {e}")
    
    async def _connect_http(self):
        """Подключение через HTTP (для удалённых MCP серверов)"""
        try:
            import urllib.request
            import urllib.error
            
            # Запрашиваем список инструментов
            req = urllib.request.Request(
                f"{self.config.command}/tools/list",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                tools = data.get("result", {}).get("tools", [])
                for tool in tools:
                    self.tools[tool["name"]] = MCPTool(
                        name=tool["name"],
                        description=tool.get("description", ""),
                        input_schema=tool.get("inputSchema", {}),
                        server_name=self.config.name
                    )
        except Exception as e:
            logger.error(f"MCP HTTP server '{self.config.name}' connection failed: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Вызов инструмента на MCP сервере"""
        if tool_name not in self.tools:
            return f"Error: Tool '{tool_name}' not found on server '{self.config.name}'"
        
        try:
            if self.config.transport == "stdio":
                return await self._call_tool_stdio(tool_name, arguments)
            elif self.config.transport == "http":
                return await self._call_tool_http(tool_name, arguments)
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            return f"Error calling {tool_name}: {e}"
    
    async def _call_tool_stdio(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Вызов инструмента через stdio"""
        call_msg = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        self.process.stdin.write(json.dumps(call_msg) + "\n")
        self.process.stdin.flush()
        
        response = self.process.stdout.readline()
        if response:
            data = json.loads(response)
            content = data.get("result", {}).get("content", [])
            if content:
                return "\n".join(c.get("text", "") for c in content)
        return "No response from MCP server"
    
    async def _call_tool_http(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Вызов инструмента через HTTP"""
        import urllib.request
        data = json.dumps({
            "name": tool_name,
            "arguments": arguments
        }).encode()
        
        req = urllib.request.Request(
            f"{self.config.command}/tools/call",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            content = result.get("result", {}).get("content", [])
            if content:
                return "\n".join(c.get("text", "") for c in content)
        return "No response from MCP server"
    
    def disconnect(self):
        """Отключение от MCP сервера"""
        if self.process:
            self.process.terminate()
            self.process = None
        self._connected = False


class MCPManager:
    """Менеджер MCP серверов"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self._load_config()
    
    def _load_config(self):
        """Загрузка конфигурации MCP серверов"""
        config_path = Path(__file__).parent.parent / "config" / "mcp_servers.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
                for server_conf in data.get("servers", []):
                    config = MCPServerConfig(**server_conf)
                    self.servers[config.name] = MCPServer(config)
            except Exception as e:
                logger.warning(f"Failed to load MCP config: {e}")
    
    async def connect_all(self):
        """Подключение ко всем включённым MCP серверам"""
        for name, server in self.servers.items():
            if server.config.enabled:
                try:
                    await server.connect()
                except Exception as e:
                    logger.warning(f"Failed to connect MCP server '{name}': {e}")
    
    def get_all_tools(self) -> List[MCPTool]:
        """Получить все инструменты со всех MCP серверов"""
        tools = []
        for server in self.servers.values():
            if server._connected:
                tools.extend(server.tools.values())
        return tools
    
    def get_tools_description(self) -> str:
        """Получить описание всех инструментов для промпта"""
        tools = self.get_all_tools()
        if not tools:
            return ""
        
        lines = ["## MCP TOOLS (External)"]
        for tool in tools:
            lines.append(f"\n### {tool.name} (from {tool.server_name})")
            lines.append(tool.description)
            if tool.input_schema:
                props = tool.input_schema.get("properties", {})
                if props:
                    lines.append("Parameters:")
                    for prop_name, prop_def in props.items():
                        desc = prop_def.get("description", "")
                        lines.append(f"  - {prop_name}: {desc}")
        return "\n".join(lines)
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Вызвать инструмент на конкретном MCP сервере"""
        if server_name in self.servers:
            return await self.servers[server_name].call_tool(tool_name, arguments)
        return f"Error: MCP server '{server_name}' not found"
    
    def disconnect_all(self):
        """Отключение от всех MCP серверов"""
        for server in self.servers.values():
            server.disconnect()


# Глобальный экземпляр
mcp_manager = MCPManager()
