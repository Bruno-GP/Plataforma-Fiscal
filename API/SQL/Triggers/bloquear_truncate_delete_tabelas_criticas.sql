-- Protecao contra exclusao destrutiva em tabelas criticas.
-- DELETE continua bloqueado para todos.
-- TRUNCATE somente para usuarios que tenham o role fiscal_admin no PostgreSQL.

CREATE OR REPLACE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_e_admin boolean := false;
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        v_e_admin := CASE
            WHEN EXISTS (
                SELECT 1
                FROM pg_roles
                WHERE rolname = 'fiscal_admin'
            ) THEN pg_has_role(current_user, 'fiscal_admin', 'MEMBER')
            ELSE false
        END
        OR EXISTS (
            SELECT 1
            FROM pg_roles
            WHERE rolname = current_user
              AND rolsuper
        );

        IF v_e_admin THEN
            RETURN NULL;
        END IF;
    END IF;

    RAISE EXCEPTION 'truncate ou delete não autorizado para a tabela %', TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS trg_bloquear_truncate_empresas ON public.empresas;
CREATE TRIGGER trg_bloquear_truncate_empresas
BEFORE TRUNCATE ON public.empresas
FOR EACH STATEMENT
EXECUTE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica();

DROP TRIGGER IF EXISTS trg_bloquear_delete_empresas ON public.empresas;
CREATE TRIGGER trg_bloquear_delete_empresas
BEFORE DELETE ON public.empresas
FOR EACH ROW
EXECUTE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica();

DROP TRIGGER IF EXISTS trg_bloquear_truncate_login ON public.login;
CREATE TRIGGER trg_bloquear_truncate_login
BEFORE TRUNCATE ON public.login
FOR EACH STATEMENT
EXECUTE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica();

DROP TRIGGER IF EXISTS trg_bloquear_delete_login ON public.login;
CREATE TRIGGER trg_bloquear_delete_login
BEFORE DELETE ON public.login
FOR EACH ROW
EXECUTE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica();

DROP TRIGGER IF EXISTS trg_bloquear_truncate_ncm_catalogo ON public.ncm_catalogo;
CREATE TRIGGER trg_bloquear_truncate_ncm_catalogo
BEFORE TRUNCATE ON public.ncm_catalogo
FOR EACH STATEMENT
EXECUTE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica();

DROP TRIGGER IF EXISTS trg_bloquear_delete_ncm_catalogo ON public.ncm_catalogo;
CREATE TRIGGER trg_bloquear_delete_ncm_catalogo
BEFORE DELETE ON public.ncm_catalogo
FOR EACH ROW
EXECUTE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica();

DROP TRIGGER IF EXISTS trg_bloquear_truncate_ncm_tributacao ON public.ncm_tributacao;
CREATE TRIGGER trg_bloquear_truncate_ncm_tributacao
BEFORE TRUNCATE ON public.ncm_tributacao
FOR EACH STATEMENT
EXECUTE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica();

DROP TRIGGER IF EXISTS trg_bloquear_delete_ncm_tributacao ON public.ncm_tributacao;
CREATE TRIGGER trg_bloquear_delete_ncm_tributacao
BEFORE DELETE ON public.ncm_tributacao
FOR EACH ROW
EXECUTE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica();

DROP TRIGGER IF EXISTS trg_bloquear_truncate_municipios_catalogo ON public.municipios_catalogo;
CREATE TRIGGER trg_bloquear_truncate_municipios_catalogo
BEFORE TRUNCATE ON public.municipios_catalogo
FOR EACH STATEMENT
EXECUTE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica();

DROP TRIGGER IF EXISTS trg_bloquear_delete_municipios_catalogo ON public.municipios_catalogo;
CREATE TRIGGER trg_bloquear_delete_municipios_catalogo
BEFORE DELETE ON public.municipios_catalogo
FOR EACH ROW
EXECUTE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica();

DROP TRIGGER IF EXISTS trg_bloquear_truncate_notas_cfops ON public.notas_cfops;
CREATE TRIGGER trg_bloquear_truncate_notas_cfops
BEFORE TRUNCATE ON public.notas_cfops
FOR EACH STATEMENT
EXECUTE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica();

DROP TRIGGER IF EXISTS trg_bloquear_delete_notas_cfops ON public.notas_cfops;
CREATE TRIGGER trg_bloquear_delete_notas_cfops
BEFORE DELETE ON public.notas_cfops
FOR EACH ROW
EXECUTE FUNCTION public.fn_bloquear_truncate_delete_tabela_critica();
