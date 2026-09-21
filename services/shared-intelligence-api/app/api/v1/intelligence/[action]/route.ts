import { NextResponse } from "next/server";
import { appendUnique, isFresh, pullRows, requireAuth } from "../_lib";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ action: string }> },
) {
  try {
    requireAuth(request);
    const { action } = await params;
    if (action === "health") {
      return NextResponse.json({
        service: "vazao-shared-intelligence",
        status: "ok",
        execution_authority: false,
        financial_state_sync: false,
        timestamp_ms: Date.now(),
      });
    }
    if (action !== "bootstrap" && action !== "pull") {
      return NextResponse.json({ error: "unsupported_action" }, { status: 404 });
    }
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get("limit") || "500");
    const cursor = action === "bootstrap" ? null : url.searchParams.get("cursor");
    const result = await pullRows(cursor, Number.isFinite(limit) ? limit : 500);
    const rows = result.rows.filter((row) => isFresh(row.artifact));
    return NextResponse.json({
      ...result,
      rows,
      count: rows.length,
      bootstrap: action === "bootstrap",
    });
  } catch (error) {
    if (error instanceof Response) return error;
    return NextResponse.json({ error: String(error) }, { status: 400 });
  }
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ action: string }> },
) {
  try {
    requireAuth(request);
    const { action } = await params;
    if (action !== "push") {
      return NextResponse.json({ error: "unsupported_action" }, { status: 404 });
    }
    const body = await request.json();
    if (!Array.isArray(body?.rows)) {
      return NextResponse.json({ error: "rows_required" }, { status: 400 });
    }
    const accepted = await appendUnique(body.rows);
    return NextResponse.json({
      accepted,
      rejected: Math.max(0, body.rows.length - accepted),
    });
  } catch (error) {
    if (error instanceof Response) return error;
    return NextResponse.json({ error: String(error) }, { status: 400 });
  }
}
