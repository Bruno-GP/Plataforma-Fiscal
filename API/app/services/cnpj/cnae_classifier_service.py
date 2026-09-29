from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CnaeClassificationRule:
    segmento_chave: str
    segmento_nome: str
    cnae_prefixo: str | None = None
    cnae_codigo: str | None = None
    prioridade: int = 100


@dataclass(frozen=True)
class CnaeClassificationResult:
    cnae_codigo: str
    segmento_chave: str | None = None
    segmento_nome: str | None = None
    cnae_prefixo: str | None = None
    confianca: float = 0.0
    motivo: str = "CNAE principal nao mapeado."


DEFAULT_CNAE_CLASSIFICATION_RULES: tuple[CnaeClassificationRule, ...] = (
    *(
        CnaeClassificationRule("industria", "Industria", cnae_prefixo=str(prefixo), prioridade=100)
        for prefixo in range(10, 34)
    ),
    CnaeClassificationRule("comercio_varejista", "Comercio varejista", cnae_prefixo="47", prioridade=80),
    *(
        CnaeClassificationRule("transporte_logistica", "Transporte e logistica", cnae_prefixo=str(prefixo), prioridade=90)
        for prefixo in range(49, 54)
    ),
    *(
        CnaeClassificationRule("servicos_profissionais", "Servicos profissionais", cnae_prefixo=str(prefixo), prioridade=100)
        for prefixo in range(69, 76)
    ),
)


def normalizar_cnae(valor: str | int | None) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


class CnaeClassifierService:
    def __init__(self, rules: tuple[CnaeClassificationRule, ...] | None = None) -> None:
        self.rules = rules or DEFAULT_CNAE_CLASSIFICATION_RULES

    def classificar(self, cnae_fiscal: str | int | None) -> CnaeClassificationResult:
        cnae_codigo = normalizar_cnae(cnae_fiscal)
        if not cnae_codigo:
            return CnaeClassificationResult(cnae_codigo="")

        exact_rule = self._match_exact(cnae_codigo)
        if exact_rule:
            return CnaeClassificationResult(
                cnae_codigo=cnae_codigo,
                segmento_chave=exact_rule.segmento_chave,
                segmento_nome=exact_rule.segmento_nome,
                cnae_prefixo=exact_rule.cnae_prefixo,
                confianca=1.0,
                motivo=f"CNAE {cnae_codigo} mapeado por codigo exato.",
            )

        prefix_rule = self._match_prefix(cnae_codigo)
        if prefix_rule:
            return CnaeClassificationResult(
                cnae_codigo=cnae_codigo,
                segmento_chave=prefix_rule.segmento_chave,
                segmento_nome=prefix_rule.segmento_nome,
                cnae_prefixo=prefix_rule.cnae_prefixo,
                confianca=0.8,
                motivo=f"CNAE {cnae_codigo} mapeado pelo prefixo {prefix_rule.cnae_prefixo}.",
            )

        return CnaeClassificationResult(cnae_codigo=cnae_codigo)

    def _match_exact(self, cnae_codigo: str) -> CnaeClassificationRule | None:
        matches = [rule for rule in self.rules if rule.cnae_codigo == cnae_codigo]
        return self._best_rule(matches)

    def _match_prefix(self, cnae_codigo: str) -> CnaeClassificationRule | None:
        matches = [
            rule
            for rule in self.rules
            if rule.cnae_prefixo and cnae_codigo.startswith(rule.cnae_prefixo)
        ]
        matches.sort(key=lambda rule: (-len(rule.cnae_prefixo or ""), rule.prioridade))
        return matches[0] if matches else None

    @staticmethod
    def _best_rule(rules: list[CnaeClassificationRule]) -> CnaeClassificationRule | None:
        if not rules:
            return None
        return sorted(rules, key=lambda rule: rule.prioridade)[0]
