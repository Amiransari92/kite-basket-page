# kite-basket-page

Tiny static page that turns a Discord link into a Zerodha Kite Publisher basket.

1. A script stores an order list in AWS under an unguessable id and DMs a link: `.../?b=<id>`.
2. `index.html` fetches that order list and submits it as a form POST to `https://kite.zerodha.com/connect/basket`.
3. You confirm the orders on Kite's own screen. Kite sends you back to `done.html`.

No secrets live here. `api_key` is Kite Publisher's public key and comes from the stored basket;
the Kite secret is never used. Orders expire from AWS after one day.
