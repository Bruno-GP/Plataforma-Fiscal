export const validatePasswordChange = (novaSenha: string, confirmarNovaSenha: string) => {
  if (!novaSenha.trim()) {
    return 'Informe uma nova senha valida.';
  }

  if (!confirmarNovaSenha.trim()) {
    return 'Confirme a nova senha antes de continuar.';
  }

  if (novaSenha !== confirmarNovaSenha) {
    return 'As duas senhas precisam ser iguais.';
  }

  return null;
};
