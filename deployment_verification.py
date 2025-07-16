#!/usr/bin/env python3
"""
🚀 DEPLOYMENT VERIFICATION SCRIPT
Проверка готовности к production деплою

Проверяет все критические компоненты деплоя:
- Configuration files
- Environment variables
- Dependencies
- Docker setup
- Railway setup
"""

import os
import sys
import json
import subprocess
from pathlib import Path


class DeploymentVerifier:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_checks = 0

    def check(self, name, condition, error_msg="", warning_msg=""):
        """Выполнить проверку"""
        self.total_checks += 1
        print(f"[{self.total_checks:2d}] 🔍 {name}...")

        if condition:
            print(f"    ✅ {name}: OK")
            self.success_count += 1
            return True
        else:
            if error_msg:
                print(f"    ❌ {name}: {error_msg} 🚨 CRITICAL")
                self.errors.append(f"❌ {name}: {error_msg}")
            elif warning_msg:
                print(f"    ⚠️ {name}: {warning_msg}")
                self.warnings.append(f"⚠️ {name}: {warning_msg}")
            return False

    def verify_files(self):
        """Проверка конфигурационных файлов"""
        print("\n📁 CONFIGURATION FILES")
        print("="*50)

        # Procfile
        procfile_exists = Path("Procfile").exists()
        self.check("Procfile exists", procfile_exists, "Procfile not found")

        if procfile_exists:
            with open("Procfile", "r") as f:
                procfile_content = f.read()
                has_web = "web:" in procfile_content
                has_correct_entry = "production_unified_start.py" in procfile_content
                self.check("Procfile has web command", has_web,
                           "No web command in Procfile")
                self.check("Procfile has correct entry point", has_correct_entry,
                           "Incorrect entry point in Procfile")

        # railway.json
        railway_json_exists = Path("railway.json").exists()
        self.check("railway.json exists", railway_json_exists,
                   "railway.json not found")

        if railway_json_exists:
            try:
                with open("railway.json", "r") as f:
                    railway_config = json.load(f)
                    has_schema = "$schema" in railway_config
                    has_deploy = "deploy" in railway_config
                    has_healthcheck = railway_config.get(
                        "deploy", {}).get("healthcheckPath") == "/health"

                    self.check("railway.json has schema", has_schema)
                    self.check("railway.json has deploy config", has_deploy)
                    self.check("railway.json has health check",
                               has_healthcheck)
            except json.JSONDecodeError:
                self.check("railway.json is valid JSON", False,
                           "Invalid JSON in railway.json")

        # Entry points
        production_start_exists = Path("production_unified_start.py").exists()
        self.check("production_unified_start.py exists", production_start_exists,
                   "Production entry point not found")

        app_py_exists = Path("app.py").exists()
        self.check("app.py exists", app_py_exists,
                   "Web server entry point not found")

        bot_main_exists = Path("bot/main.py").exists()
        self.check("bot/main.py exists", bot_main_exists,
                   "Bot entry point not found")

        # Docker files
        dockerfile_exists = Path("Dockerfile").exists()
        self.check("Dockerfile exists", dockerfile_exists,
                   "Dockerfile not found (needed for Docker deployment)")

        docker_compose_exists = Path("docker-compose.yml").exists()
        self.check("docker-compose.yml exists", docker_compose_exists,
                   "docker-compose.yml not found (needed for Docker deployment)")

        # Requirements
        requirements_exists = Path("requirements.txt").exists()
        self.check("requirements.txt exists", requirements_exists,
                   "requirements.txt not found")

        requirements_frozen_exists = Path("requirements_frozen.txt").exists()
        self.check("requirements_frozen.txt exists", requirements_frozen_exists,
                   "requirements_frozen.txt not found")

    def verify_environment(self):
        """Проверка переменных окружения"""
        print("\n🔧 ENVIRONMENT VARIABLES")
        print("="*50)

        critical_vars = {
            'BOT_TOKEN': 'Telegram Bot Token',
            'DATABASE_URL': 'Database Connection',
            'ADMIN_CHAT_ID': 'Admin Chat ID'
        }

        optional_vars = {
            'OPENAI_API_KEY': 'OpenAI API Key',
            'OPENROUTER_API_KEY': 'OpenRouter API Key',
            'CLOUDPAYMENTS_PUBLIC_ID': 'CloudPayments Public ID',
            'CLOUDPAYMENTS_API_SECRET': 'CloudPayments API Secret',
            'TARGET_CHANNEL_ID': 'Target Channel ID'
        }

        # Critical variables
        for var, desc in critical_vars.items():
            value = os.getenv(var)
            self.check(f"Environment: {var}", bool(value), f"{desc} not set")

        # Optional variables
        for var, desc in optional_vars.items():
            value = os.getenv(var)
            self.check(f"Environment: {var}", bool(
                value), "", f"{desc} not set (optional)")

    def verify_dependencies(self):
        """Проверка зависимостей"""
        print("\n📦 DEPENDENCIES")
        print("="*50)

        critical_packages = [
            'python-telegram-bot',
            'fastapi',
            'uvicorn',
            'sqlalchemy',
            'asyncpg',
            'aiohttp'
        ]

        for package in critical_packages:
            try:
                result = subprocess.run([sys.executable, '-c', f'import {package.replace("-", "_")}'],
                                        capture_output=True, text=True)
                self.check(f"Package: {package}", result.returncode == 0,
                           f"{package} not installed")
            except Exception:
                self.check(f"Package: {package}", False,
                           f"Cannot check {package}")

    def verify_deployment_readiness(self):
        """Проверка готовности к деплою"""
        print("\n🚀 DEPLOYMENT READINESS")
        print("="*50)

        # Git repository
        git_exists = Path(".git").exists()
        self.check("Git repository", git_exists, "Not a git repository")

        if git_exists:
            try:
                # Check if there are uncommitted changes
                result = subprocess.run(['git', 'status', '--porcelain'],
                                        capture_output=True, text=True)
                is_clean = len(result.stdout.strip()) == 0
                self.check("Git working tree clean", is_clean, "",
                           "Uncommitted changes (should commit before deploy)")

                # Check if we're on main branch
                result = subprocess.run(['git', 'branch', '--show-current'],
                                        capture_output=True, text=True)
                is_main = result.stdout.strip() == 'main'
                self.check("On main branch", is_main, "",
                           "Not on main branch (recommended for production)")
            except Exception:
                self.check("Git status check", False,
                           "", "Cannot check git status")

        # Health check endpoint
        try:
            from app import app
            self.check("FastAPI app importable", True)
        except Exception as e:
            self.check("FastAPI app importable", False,
                       f"Cannot import app: {e}")

        # Bot importable
        try:
            from bot.main import main
            self.check("Bot main importable", True)
        except Exception as e:
            self.check("Bot main importable", False, f"Cannot import bot: {e}")

    def generate_report(self):
        """Генерация финального отчета"""
        print("\n" + "="*60)
        print("🎯 DEPLOYMENT VERIFICATION REPORT")
        print("="*60)

        success_rate = (self.success_count / self.total_checks) * 100

        print(f"📊 **VERIFICATION SUMMARY:**")
        print(f"   Total Checks: {self.total_checks}")
        print(f"   ✅ Passed: {self.success_count}")
        print(f"   ❌ Failed: {len(self.errors)}")
        print(f"   ⚠️ Warnings: {len(self.warnings)}")
        print(f"   📈 Success Rate: {success_rate:.1f}%")

        # Deployment readiness
        if len(self.errors) == 0:
            if len(self.warnings) == 0:
                print(f"\n🚀 **DEPLOYMENT STATUS:** 🟢 READY FOR PRODUCTION")
                print(f"   Recommendation: ✅ Ready for immediate deployment")
            else:
                print(f"\n🚀 **DEPLOYMENT STATUS:** 🟡 READY WITH WARNINGS")
                print(f"   Recommendation: ⚠️ Can deploy but review warnings")
        else:
            print(f"\n🚀 **DEPLOYMENT STATUS:** 🔴 NOT READY")
            print(f"   Recommendation: 🚨 Fix critical issues before deployment")

        # Error details
        if self.errors:
            print(f"\n🚨 **CRITICAL ISSUES ({len(self.errors)}):**")
            for error in self.errors:
                print(f"   {error}")

        # Warning details
        if self.warnings:
            print(f"\n⚠️ **WARNINGS ({len(self.warnings)}):**")
            for warning in self.warnings:
                print(f"   {warning}")

        print(
            f"\n🕐 Verification Completed: {__import__('datetime').datetime.now()}")
        print("="*60)

        return len(self.errors) == 0


def main():
    print("🚀 DEPLOYMENT VERIFICATION")
    print("="*60)
    print(
        f"📅 Verification Time: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target: Production Deployment Readiness")
    print("="*60)

    verifier = DeploymentVerifier()

    # Run all verifications
    verifier.verify_files()
    verifier.verify_environment()
    verifier.verify_dependencies()
    verifier.verify_deployment_readiness()

    # Generate final report
    ready = verifier.generate_report()

    # Exit with appropriate code
    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    main()
