import { NextResponse } from "next/server";
export const dynamic = "force-dynamic";
export function GET() { return NextResponse.json({ok:true,service:"vazao-shared-learning",version:1},{headers:{"Cache-Control":"no-store"}}); }
