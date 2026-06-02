import { loginFlow } from './login.flow.js';
import { dashboardFlow } from './dashboard.flow.js';
import { consultaFlow } from './consulta.flow.js';
import { operacaoCriticaFlow } from './operacaoCritica.flow.js';
import { think } from '../helpers/httpClient.js';

export function jornadaCompleta() {
  const auth = loginFlow();
  think(0.2, 0.8);

  dashboardFlow(auth.session);
  think(0.3, 1);

  consultaFlow(auth.session);
  think(0.3, 1);

  operacaoCriticaFlow(auth.session);
  think(0.5, 1.5);
}
