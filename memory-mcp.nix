{ pkgs }:

pkgs.python3Packages.buildPythonApplication {
  pname = "memory-mcp";
  version = "0.1.0";

  src = pkgs.fetchFromGitHub {
    owner = "mickael-koenig";
    repo = "memory-mcp";
    rev = "HEAD";
    hash = "";
  };

  format = "pyproject";

  dependencies = with pkgs.python3Packages; [
    faiss-cpu
    mcp
    python-dotenv
    requests
    pydantic
    openai
  ];

  build-system = with pkgs.python3Packages; [
    hatchling
  ];

  pythonImportsCheck = [ "memory_mcp" ];
}
