// Reglas de CS2 Premier: los umbrales de rango (cambio de color) caen cada
// 5,000 puntos (5k, 10k, 15k, 20k, 25k, 30k). El jugador entra en "Partida
// de Ascenso" cuando su rating es el último punto antes del umbral, es
// decir X,999 (4999 / 9999 / 14999 / 19999 / 24999).
export function isPromotionalMatch(rating: number): boolean {
  return rating % 5000 === 4999;
}
