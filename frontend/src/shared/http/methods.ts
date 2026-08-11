const MUTATION_METHODS = new Set(['post', 'put', 'patch', 'delete']);

export function isMutationMethod(method: string | undefined): boolean {
  return method ? MUTATION_METHODS.has(method.toLowerCase()) : false;
}
