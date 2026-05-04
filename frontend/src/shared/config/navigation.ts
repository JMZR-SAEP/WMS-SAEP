type NavigationItem = {
  to:
    | "/"
    | "/login"
    | "/minhas-requisicoes"
    | "/requisicoes/nova"
    | "/requisicoes/$id"
    | "/autorizacoes"
    | "/atendimentos";
  label: string;
  hint: string;
  tag: string;
  params?: {
    id: string;
  };
  matches: (pathname: string) => boolean;
};

export const navigationItems: NavigationItem[] = [
  {
    to: "/",
    label: "Mapa da fundação",
    hint: "shell",
    tag: "Scaffold",
    matches: (pathname: string) => pathname === "/",
  },
  {
    to: "/login",
    label: "Login",
    hint: "#37",
    tag: "Auth",
    matches: (pathname: string) => pathname === "/login",
  },
  {
    to: "/minhas-requisicoes",
    label: "Minhas requisições",
    hint: "#38",
    tag: "Lista",
    matches: (pathname: string) => pathname === "/minhas-requisicoes",
  },
  {
    to: "/requisicoes/nova",
    label: "Nova requisição",
    hint: "#39",
    tag: "Draft",
    matches: (pathname: string) => pathname === "/requisicoes/nova",
  },
  {
    to: "/requisicoes/$id",
    params: {
      id: "9001",
    },
    label: "Detalhe canônico",
    hint: "#38",
    tag: "Detail",
    matches: (pathname: string) =>
      pathname !== "/requisicoes/nova" && /^\/requisicoes\/[^/]+$/.test(pathname),
  },
  {
    to: "/autorizacoes",
    label: "Fila de autorizações",
    hint: "#40",
    tag: "Queue",
    matches: (pathname: string) => pathname === "/autorizacoes",
  },
  {
    to: "/atendimentos",
    label: "Fila de atendimento",
    hint: "#41",
    tag: "Queue",
    matches: (pathname: string) => pathname === "/atendimentos",
  },
];
