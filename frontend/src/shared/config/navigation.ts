type NavigationItem = {
  to:
    | "/alertas"
    | "/atendimentos"
    | "/autorizacoes"
    | "/minhas-requisicoes"
    | "/requisicoes/nova";
  label: string;
  visibleFor?: string[];
  matches: (pathname: string) => boolean;
};

export const navigationItems: NavigationItem[] = [
  {
    to: "/minhas-requisicoes",
    label: "Minhas requisições",
    matches: (pathname) => pathname === "/minhas-requisicoes",
  },
  {
    to: "/requisicoes/nova",
    label: "Nova requisição",
    matches: (pathname) => pathname === "/requisicoes/nova",
  },
  {
    to: "/autorizacoes",
    label: "Fila de autorizações",
    visibleFor: ["chefe_setor", "chefe_almoxarifado"],
    matches: (pathname) => pathname === "/autorizacoes",
  },
  {
    to: "/atendimentos",
    label: "Fila de atendimento",
    visibleFor: ["auxiliar_almoxarifado", "chefe_almoxarifado"],
    matches: (pathname) => pathname === "/atendimentos",
  },
  {
    to: "/alertas",
    label: "Alertas",
    visibleFor: ["chefe_setor", "chefe_almoxarifado"],
    matches: (pathname) => pathname === "/alertas",
  },
];
