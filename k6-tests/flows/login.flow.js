import { group } from 'k6';
import { getTestUser, login, validateAuthenticatedSession } from '../helpers/auth.js';

export function loginFlow() {
  return group('login', () => {
    const auth = login();
    const session = validateAuthenticatedSession(getTestUser().email);

    return {
      ...auth,
      session: session || auth.session,
    };
  });
}
