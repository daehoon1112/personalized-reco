rootProject.name = "personalized-reco"

// JVM(Kotlin) 측 모듈. Python(uv) 측은 루트 pyproject.toml 워크스페이스로 별도 관리.
include("apps:serving")
