"""原 MCP 工具的机械迁移；函数体和参数由冻结契约校验，不修改执行逻辑。"""

from typing import Any, Dict

from .support import logger


def register(mcp, tool_client):
    """将本领域工具绑定到当前服务实例，保留实例独立的后端客户端。"""
    @mcp.tool()
    def create_file(filename: str, content: str, binary: bool = False) -> Dict[str, Any]:
        """
        Create a file with specified content on the pentest-tools server.

        Args:
            filename: Name of the file to create
            content: Content to write to the file
            binary: Whether the content is binary data

        Returns:
            File creation results
        """
        data = {
            "filename": filename,
            "content": content,
            "binary": binary
        }
        logger.info(f"📄 Creating file: {filename}")
        result = tool_client.safe_post("api/files/create", data)
        if result.get("success"):
            logger.info(f"✅ File created successfully: {filename}")
        else:
            logger.error(f"❌ Failed to create file: {filename}")
        return result

    @mcp.tool()
    def modify_file(filename: str, content: str, append: bool = False) -> Dict[str, Any]:
        """
        Modify an existing file on the pentest-tools server.

        Args:
            filename: Name of the file to modify
            content: Content to write or append
            append: Whether to append to the file (True) or overwrite (False)

        Returns:
            File modification results
        """
        data = {
            "filename": filename,
            "content": content,
            "append": append
        }
        logger.info(f"✏️  Modifying file: {filename}")
        result = tool_client.safe_post("api/files/modify", data)
        if result.get("success"):
            logger.info(f"✅ File modified successfully: {filename}")
        else:
            logger.error(f"❌ Failed to modify file: {filename}")
        return result

    @mcp.tool()
    def delete_file(filename: str) -> Dict[str, Any]:
        """
        Delete a file or directory on the pentest-tools server.

        Args:
            filename: Name of the file or directory to delete

        Returns:
            File deletion results
        """
        data = {
            "filename": filename
        }
        logger.info(f"🗑️  Deleting file: {filename}")
        result = tool_client.safe_post("api/files/delete", data)
        if result.get("success"):
            logger.info(f"✅ File deleted successfully: {filename}")
        else:
            logger.error(f"❌ Failed to delete file: {filename}")
        return result

    @mcp.tool()
    def list_files(directory: str = ".") -> Dict[str, Any]:
        """
        List files in a directory on the pentest-tools server.

        Args:
            directory: Directory to list (relative to server's base directory)

        Returns:
            Directory listing results
        """
        logger.info(f"📂 Listing files in directory: {directory}")
        result = tool_client.safe_get("api/files/list", {"directory": directory})
        if result.get("success"):
            file_count = len(result.get("files", []))
            logger.info(f"✅ Listed {file_count} files in {directory}")
        else:
            logger.error(f"❌ Failed to list files in {directory}")
        return result

    @mcp.tool()
    def generate_payload(payload_type: str = "buffer", size: int = 1024, pattern: str = "A", filename: str = "") -> Dict[str, Any]:
        """
        Generate large payloads for testing and exploitation.

        Args:
            payload_type: Type of payload (buffer, cyclic, random)
            size: Size of the payload in bytes
            pattern: Pattern to use for buffer payloads
            filename: Custom filename (auto-generated if empty)

        Returns:
            Payload generation results
        """
        data = {
            "type": payload_type,
            "size": size,
            "pattern": pattern
        }
        if filename:
            data["filename"] = filename

        logger.info(f"🎯 Generating {payload_type} payload: {size} bytes")
        result = tool_client.safe_post("api/payloads/generate", data)
        if result.get("success"):
            logger.info(f"✅ Payload generated successfully")
        else:
            logger.error(f"❌ Failed to generate payload")
        return result

    @mcp.tool()
    def install_python_package(package: str, env_name: str = "default") -> Dict[str, Any]:
        """
        Install a Python package in a virtual environment on the pentest-tools server.

        Args:
            package: Name of the Python package to install
            env_name: Name of the virtual environment

        Returns:
            Package installation results
        """
        data = {
            "package": package,
            "env_name": env_name
        }
        logger.info(f"📦 Installing Python package: {package} in env {env_name}")
        result = tool_client.safe_post("api/python/install", data)
        if result.get("success"):
            logger.info(f"✅ Package {package} installed successfully")
        else:
            logger.error(f"❌ Failed to install package {package}")
        return result

    @mcp.tool()
    def execute_python_script(script: str, env_name: str = "default", filename: str = "") -> Dict[str, Any]:
        """
        Execute a Python script in a virtual environment on the pentest-tools server.

        Args:
            script: Python script content to execute
            env_name: Name of the virtual environment
            filename: Custom script filename (auto-generated if empty)

        Returns:
            Script execution results
        """
        data = {
            "script": script,
            "env_name": env_name
        }
        if filename:
            data["filename"] = filename

        logger.info(f"🐍 Executing Python script in env {env_name}")
        result = tool_client.safe_post("api/python/execute", data)
        if result.get("success"):
            logger.info(f"✅ Python script executed successfully")
        else:
            logger.error(f"❌ Python script execution failed")
        return result
