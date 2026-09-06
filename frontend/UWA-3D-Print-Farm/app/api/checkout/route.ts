export async function POST(request: Request) {
  const secretKey = process.env.STRIPE_SECRET_KEY;
  if (!secretKey) {
    return Response.json(
      { error: "Stripe test mode is not configured yet. Add STRIPE_SECRET_KEY to the server environment." },
      { status: 503 },
    );
  }

  const { fileName } = await request.json() as { fileName?: string };
  if (!fileName || !/\.(gcode|bgcode)$/i.test(fileName)) {
    return Response.json({ error: "A valid G-code file is required." }, { status: 400 });
  }

  const origin = new URL(request.url).origin;
  const form = new URLSearchParams({
    mode: "payment",
    "line_items[0][quantity]": "1",
    "line_items[0][price_data][currency]": "aud",
    "line_items[0][price_data][unit_amount]": "1173",
    "line_items[0][price_data][product_data][name]": "3D print job",
    "line_items[0][price_data][product_data][description]": fileName,
    "metadata[fileName]": fileName,
    "metadata[estimatedDuration]": "4 hr 22 min",
    success_url: origin + "/?payment=success",
    cancel_url: origin + "/?payment=cancelled",
  });

  const stripeResponse = await fetch("https://api.stripe.com/v1/checkout/sessions", {
    method: "POST",
    headers: {
      Authorization: "Bearer " + secretKey,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: form,
  });
  const session = await stripeResponse.json() as { url?: string; error?: { message?: string } };
  if (!stripeResponse.ok || !session.url) {
    return Response.json({ error: session.error?.message || "Stripe Checkout could not be created." }, { status: 502 });
  }
  return Response.json({ url: session.url });
}
