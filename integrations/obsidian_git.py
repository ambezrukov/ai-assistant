"""
Git синхронизация для Obsidian хранилища
"""

import os
import subprocess
from typing import Optional, Dict, Any
from pathlib import Path

from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)

# Загрузить конфигурацию
config = load_config()
obsidian_config = config.get('obsidian', {})
VAULT_PATH = obsidian_config.get('vault_path', '')
GIT_ENABLED = obsidian_config.get('git_sync', {}).get('enabled', False)
GIT_AUTO_COMMIT = obsidian_config.get('git_sync', {}).get('auto_commit', True)
GIT_AUTO_PUSH = obsidian_config.get('git_sync', {}).get('auto_push', False)


class ObsidianGitSync:
    """Класс для Git синхронизации Obsidian хранилища"""

    def __init__(self, vault_path: str = None):
        """
        Инициализация Git синхронизации

        Args:
            vault_path: Путь к хранилищу Obsidian
        """
        self.vault_path = vault_path or VAULT_PATH
        self.auto_commit = GIT_AUTO_COMMIT
        self.auto_push = GIT_AUTO_PUSH

        logger.info(f"ObsidianGitSync инициализирован (путь: {self.vault_path})")

    def is_git_repo(self) -> bool:
        """
        Проверяет, является ли хранилище Git репозиторием

        Returns:
            True если это Git репозиторий
        """
        git_dir = os.path.join(self.vault_path, '.git')
        return os.path.exists(git_dir) and os.path.isdir(git_dir)

    def git_pull(self) -> Dict[str, Any]:
        """
        Выполняет git pull перед чтением/редактированием

        Returns:
            Результат операции
        """
        if not self.is_git_repo():
            return {'success': False, 'message': 'Не является Git репозиторием'}

        try:
            logger.info("Выполнение git pull...")

            result = subprocess.run(
                ['git', 'pull'],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"Git pull успешно: {result.stdout.strip()}")
                return {
                    'success': True,
                    'message': 'Git pull выполнен успешно',
                    'output': result.stdout.strip()
                }
            else:
                logger.warning(f"Git pull завершился с ошибкой: {result.stderr}")
                return {
                    'success': False,
                    'message': f'Git pull ошибка: {result.stderr}',
                    'output': result.stderr
                }

        except subprocess.TimeoutExpired:
            logger.error("Git pull timeout")
            return {'success': False, 'message': 'Git pull timeout'}

        except Exception as e:
            logger.error(f"Ошибка git pull: {e}", exc_info=True)
            return {'success': False, 'message': f'Ошибка: {str(e)}'}

    def git_commit_and_push(self, message: str = "Auto-commit from AI Assistant") -> Dict[str, Any]:
        """
        Выполняет git commit и push после изменений

        Args:
            message: Сообщение коммита

        Returns:
            Результат операции
        """
        if not self.is_git_repo():
            return {'success': False, 'message': 'Не является Git репозиторием'}

        try:
            # Проверить, есть ли изменения
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if not status_result.stdout.strip():
                logger.debug("Нет изменений для коммита")
                return {'success': True, 'message': 'Нет изменений'}

            # Git add .
            logger.info("Добавление файлов (git add)...")
            add_result = subprocess.run(
                ['git', 'add', '.'],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if add_result.returncode != 0:
                logger.error(f"Git add ошибка: {add_result.stderr}")
                return {'success': False, 'message': f'Git add ошибка: {add_result.stderr}'}

            # Git commit
            logger.info(f"Создание коммита: {message}")
            commit_result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if commit_result.returncode != 0:
                logger.error(f"Git commit ошибка: {commit_result.stderr}")
                return {'success': False, 'message': f'Git commit ошибка: {commit_result.stderr}'}

            commit_output = commit_result.stdout.strip()
            logger.info(f"Коммит создан: {commit_output}")

            result = {
                'success': True,
                'message': 'Коммит создан успешно',
                'commit_output': commit_output
            }

            # Git push (если включен auto_push)
            if self.auto_push:
                logger.info("Выполнение git push...")
                push_result = subprocess.run(
                    ['git', 'push'],
                    cwd=self.vault_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if push_result.returncode == 0:
                    logger.info("Git push успешно")
                    result['message'] = 'Коммит и push выполнены успешно'
                    result['push_output'] = push_result.stdout.strip()
                else:
                    logger.warning(f"Git push ошибка: {push_result.stderr}")
                    result['push_error'] = push_result.stderr

            return result

        except subprocess.TimeoutExpired:
            logger.error("Git операция timeout")
            return {'success': False, 'message': 'Git timeout'}

        except Exception as e:
            logger.error(f"Ошибка git операции: {e}", exc_info=True)
            return {'success': False, 'message': f'Ошибка: {str(e)}'}

    def sync_before_operation(self) -> bool:
        """
        Синхронизация перед операцией (pull)

        Returns:
            True если синхронизация успешна или не требуется
        """
        if not GIT_ENABLED:
            return True

        result = self.git_pull()
        return result.get('success', False)

    def sync_after_operation(self, operation_description: str = "AI Assistant operation") -> bool:
        """
        Синхронизация после операции (commit + push)

        Args:
            operation_description: Описание операции для сообщения коммита

        Returns:
            True если синхронизация успешна или не требуется
        """
        if not GIT_ENABLED or not self.auto_commit:
            return True

        message = f"Auto-commit: {operation_description}"
        result = self.git_commit_and_push(message)
        return result.get('success', False)


# Глобальный экземпляр
_git_sync_instance = None


def get_git_sync() -> Optional[ObsidianGitSync]:
    """
    Получить глобальный экземпляр ObsidianGitSync

    Returns:
        ObsidianGitSync если включен, иначе None
    """
    global _git_sync_instance

    if not GIT_ENABLED:
        return None

    if _git_sync_instance is None:
        _git_sync_instance = ObsidianGitSync()

    return _git_sync_instance
