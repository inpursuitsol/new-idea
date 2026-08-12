import { NextResponse } from "next/server";
import { buildForecast } from "@/lib/forecast";
import { fetchNiftyBars } from "@/lib/nifty";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  try {
    const { bars, meta } = await fetchNiftyBars("1y");
    const forecast = buildForecast(bars, meta);
    return NextResponse.json(forecast, {
      headers: {
        "Cache-Control": "public, s-maxage=120, stale-while-revalidate=300",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
