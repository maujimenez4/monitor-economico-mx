import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({ baseURL: BASE })

export const getLatest = () =>
  api.get('/indicadores/latest').then(r => r.data)

export const getHistorico = (serieId, dias = 30) =>
  api.get('/indicadores/historico', {
    params: { serie_id: serieId, dias }
  }).then(r => r.data)