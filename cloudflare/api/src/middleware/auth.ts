/**
 * Authentication middleware
 */

import { Context, Next } from 'hono';
import type { Env } from '../types';

export async function authMiddleware(c: Context<{ Bindings: Env }>, next: Next) {
  const authHeader = c.req.header('Authorization');

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return c.json({ error: 'Unauthorized - Missing or invalid Authorization header' }, 401);
  }

  const token = authHeader.substring(7);

  if (token !== c.env.API_KEY) {
    return c.json({ error: 'Unauthorized - Invalid API key' }, 401);
  }

  await next();
}
