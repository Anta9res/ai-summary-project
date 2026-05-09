"""
测试 qwen_client API 客户端（mock 测试）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock

import qwen_client


class TestQwenClient:
    FAKE_KEY = "sk-test-mock-key"

    def test_upload_file_nonexistent_returns_none(self):
        result = qwen_client.upload_file("/nonexistent/file.pdf", api_key=self.FAKE_KEY)
        assert result is None

    def test_process_text_file_nonexistent_returns_false(self):
        success, msg, _ = qwen_client.process_text_file(
            "/nonexistent/file.md", "question", api_key=self.FAKE_KEY
        )
        assert success is False
        assert "不存在" in msg

    def test_extract_content_from_pdf_nonexistent(self):
        path, saved = qwen_client.extract_content_from_pdf(
            "/nonexistent/file.pdf", api_key=self.FAKE_KEY
        )
        assert isinstance(path, str)
        assert saved is None

    def test_default_base_url_is_set(self):
        assert qwen_client._DEFAULT_BASE_URL == "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def test_no_module_level_api_key(self):
        assert not hasattr(qwen_client, 'API_KEY')

    def test_chat_with_tools_requires_api_key(self):
        with patch('qwen_client.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("Invalid API key")

            result, msgs, log = qwen_client.chat_with_tools(
                question="test",
                tools=[],
                tool_handlers={},
                api_key=self.FAKE_KEY,
                max_iterations=1
            )
            assert isinstance(result, str)
            assert "Invalid API key" in result
