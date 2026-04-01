{ pkgs }:

pkgs.python3Packages.buildPythonApplication {
  pname = "opencode-memory";
  version = "0.4.0";

  src = pkgs.fetchFromGitHub {
    owner = "Mickael-Roger";
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
