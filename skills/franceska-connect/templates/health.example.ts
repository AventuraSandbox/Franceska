// app/api/health/route.ts (Next.js). Replace db with your client.
import { NextResponse } from 'next/server';
import { db } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    await db.execute('select 1');
    return NextResponse.json({ ok: true, time: new Date().toISOString() });
  } catch {
    return NextResponse.json({ ok: false }, { status: 503 });
  }
}
