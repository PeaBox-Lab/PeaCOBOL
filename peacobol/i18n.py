"""Internationalization (i18n) framework for PeaCOBOL GUI."""

import json
from pathlib import Path
from typing import Dict, Optional

_DEFAULTS: Dict[str, str] = {
    "title": "PeaCOBOL Project Manager",
    "ready": "Ready",
    "success": "Operation completed successfully.",
    "error": "An error occurred.",
    "project": "Project",
    "select_project": "Select Project",
    "new_project": "New Project",
    "results": "Results",
    "scan": "Scan COBOL source",
    "assure": "Analyze COBOL source",
    "diagnose": "Diagnose spool output",
    "impact": "Compare copybooks",
    "tests": "Generate test cases",
    "golden": "Golden-master compare",
    "coverage": "Import coverage data",
    "resources": "Inventory DB2/CICS/MQ",
    "db2": "DB2 compatibility check",
    "sbom": "Create SBOM",
    "scanning": "Scanning project...",
    "assuring": "Assuring project...",
    "diagnosing": "Diagnosing project...",
    "generating": "Generating test cases...",
    "comparing": "Comparing golden files...",
    "importing": "Importing coverage...",
    "inventorying": "Inventorying resources...",
    "checking": "Checking DB2 compatibility...",
    "creating": "Creating SBOM...",
}

# Extended translations for common languages
_TRANSLATIONS = {
    "Spanish": {
        "title": "Gestor de Proyectos PeaCOBOL",
        "ready": "Listo",
        "success": "Operación completada con éxito.",
        "error": "Se produjo un error.",
        "project": "Proyecto",
        "select_project": "Seleccionar Proyecto",
        "new_project": "Nuevo Proyecto",
        "results": "Resultados",
        "scan": "Analizar fuente COBOL",
        "assure": "Analizar fuente COBOL",
        "diagnose": "Diagnosticar salida spool",
        "impact": "Comparar copias de seguridad",
        "tests": "Generar casos de prueba",
        "golden": "Comparar contra maestra dorada",
        "coverage": "Importar cobertura de datos",
        "resources": "Inventario DB2/CICS/MQ",
        "db2": "Verificar compatibilidad con DB2",
        "sbom": "Crear SBOM",
        "scanning": "Analizando proyecto...",
        "assuring": "Assegurando proyecto...",
        "diagnosing": "Diagnosticando...",
        "generating": "Generando casos de prueba...",
        "comparing": "Comparando archivos dorados...",
        "importing": "Importando cobertura...",
        "inventorying": "Inventariando recursos...",
        "checking": "Verificando compatibilidad con DB2...",
        "creating": "Creando SBOM...",
    },
    "French": {
        "title": "Gestionnaire de Projets PeaCOBOL",
        "ready": "Prêt",
        "success": "Opération terminée avec succès.",
        "error": "Une erreur s'est produite.",
        "project": "Projet",
        "select_project": "Sélectionner le Projet",
        "new_project": "Nouveau Projet",
        "results": "Résultats",
        "scan": "Analyser la source COBOL",
        "assure": "Analyser la source COBOL",
        "diagnose": "Diagnosticer la sortie spool",
        "impact": "Comparer les copies",
        "tests": "Générer les cas de test",
        "golden": "Comparer contre la master golden",
        "coverage": "Importer les données de couverture",
        "resources": "Inventaire DB2/CICS/MQ",
        "db2": "Vérifier la compatibilité DB2",
        "sbom": "Créer l'SBOM",
        "scanning": "Analyse du projet...",
        "assuring": "Assurance du projet...",
        "diagnosing": "Diagnostic...",
        "generating": "Génération des cas de test...",
        "comparing": "Comparation des maîtres dorés...",
        "importing": "Importation de la couverture...",
        "inventorying": "Inventaire des ressources...",
        "checking": "Vérification de la compatibilité DB2...",
        "creating": "Création de l'SBOM...",
    },
    "German": {
        "title": "PeaCOBOL-Projektmanager",
        "ready": "Bereit",
        "success": "Aufgabe erfolgreich abgeschlossen.",
        "error": "Ein Fehler ist aufgetreten.",
        "project": "Projekt",
        "select_project": "Projekt auswählen",
        "new_project": "Neues Projekt",
        "results": "Ergebnisse",
        "scan": "COBOL-Quelle analysieren",
        "assure": "COBOL-Quelle analysieren",
        "diagnose": "Spool-Ausgabe diagnostizieren",
        "impact": "Kopien vergleichen",
        "tests": "Testfälle generieren",
        "golden": "Golden-Master vergleichen",
        "coverage": "Abdeckung importieren",
        "resources": "DB2/CICS/MQ-Ressourcen Inventar",
        "db2": "DB2-Kompatibilität überprüfen",
        "sbom": "SBOM erstellen",
        "scanning": "Projekt analysieren...",
        "assuring": "Projekt absichern...",
        "diagnosing": "Diagnostizierung...",
        "generating": "Testfälle generieren...",
        "comparing": "Golden-Master vergleichen...",
        "importing": "Abdeckung importieren...",
        "inventorying": "Ressourcen inventarisieren...",
        "checking": "DB2-Kompatibilität überprüfen...",
        "creating": "SBOM erstellen...",
    },
    "Chinese": {
        "title": "PeaCOBOL 项目管理器",
        "ready": "就绪",
        "success": "操作成功完成。",
        "error": "发生错误。",
        "project": "项目",
        "select_project": "选择项目",
        "new_project": "新建项目",
        "results": "结果",
        "scan": "扫描 COBOL 源代码",
        "assure": "分析 COBOL 源代码",
        "diagnose": "诊断转储输出",
        "impact": "比较副本文件",
        "tests": "生成测试用例",
        "golden": "黄金主对比",
        "coverage": "导入覆盖率数据",
        "resources": "资源清单 DB2/CICS/MQ",
        "db2": "DB2 兼容性检查",
        "sbom": "创建 SBOM",
        "scanning": "正在扫描项目...",
        "assuring": "正在分析项目...",
        "diagnosing": "诊断中...",
        "generating": "正在生成测试用例...",
        "comparing": "正在比较黄金文件...",
        "importing": "正在导入覆盖率...",
        "inventorying": "正在盘点资源...",
        "checking": "正在检查 DB2 兼容性...",
        "creating": "正在创建 SBOM...",
    },
}


class I18N:
    """Simple translation manager."""

    def __init__(self, lang: Optional[str] = None):
        self._lang = lang or "English"
        self._table = dict(_DEFAULTS)
        extra = _TRANSLATIONS.get(self._lang)
        if extra:
            self._table.update(extra)

    def set_language(self, lang: str):
        if lang in _TRANSLATIONS:
            self._lang = lang
            self._table.update(_TRANSLATIONS[lang])
        else:
            self._lang = lang
            self._table = dict(_DEFAULTS)

    def get(self, key: str) -> str:
        return self._table.get(key, _DEFAULTS.get(key, key))
