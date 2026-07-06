# for-U API contract (captured live from vons.com, 2026-07-06)

Confirmed against Sam's logged-in vons.com session (store 3326, Turnpike Rd, Santa Barbara)
by capturing the two real requests as cURL from Chrome DevTools. **No tokens, cookies, or PII
are stored in this repo** — every credential below is shown as a `<PLACEHOLDER>`. The real
values live only in the captured session at runtime.

## Auth material (from cookies, never committed)

- `SWY_SHARED_SESSION` cookie → URL-decoded JSON → `.accessToken` = the Okta JWT used as the
  bearer/sso token. Also carries `.refreshToken`, `.issueTime`, `.expireTime`.
- `SWY_SHARED_SESSION_INFO` cookie → URL-decoded JSON → `.info.J4U.storeId` = `3326` (confirmed).

## Endpoint 1 — list offers (GET)

```
GET https://www.vons.com/abs/pub/xapi/offers/companiongalleryoffer
    ?storeId=3326&rand=<6-digit>&includeRedmBonusPathFPOffers=true
```

Headers:
- `authorization: Bearer <ACCESS_TOKEN>`
- `accept: application/json`
- `content-type: application/vnd.safeway.v2+json`
- `x-swy_api_key: emjou`
- `x-swy_banner: vons`
- `x-swy_version: 1.1`
- `x-swy-application-type: web`

## Endpoint 2 — clip offer (POST)  ← routes through the IBM API gateway

```
POST https://www.vons.com/abs/pub/web/j4u/api/offers/clip?storeId=3326
```

Headers (differ from the GET — note the token goes in `swy_sso_token`, NOT `authorization`,
and this endpoint additionally requires IBM gateway credentials):
- `swy_sso_token: <ACCESS_TOKEN>`
- `x-swyconsumerdirectorypro: <ACCESS_TOKEN>`  (same JWT again)
- `x-ibm-client-id: <IBM_CLIENT_ID>`
- `x-ibm-client-secret: <IBM_CLIENT_SECRET>`
- `x-swy-correlation-id: <fresh uuid4 per request>`
- `x-swy_api_key: emjou`
- `x-swy_banner: vons`
- `x-swy_version: 1.0`   (note: 1.0 here, 1.1 on the GET)
- `content-type: application/json`
- `accept: application/json, text/plain, */*`
- `origin: https://www.vons.com`

Request body (confirmed exactly — matches the C+L two-item pattern from the design):

```json
{"items":[{"clipType":"C","itemId":"79317412","itemType":"MF"},
          {"clipType":"L","itemId":"79317412","itemType":"MF"}]}
```

`itemId` = the offer id; `itemType` = the offer program (`SC` store coupon, `MF` manufacturer,
`PD` personalized deal). Two items per clip: one `clipType:"C"`, one `clipType:"L"`.

## Not yet captured

The offer-list **response body** was not captured (only the request). The parsed shape
(`companionGalleryOfferList` array of offers with `offerId`/`status`/`offerPgm`) is derived from
the smkent/safeway-coupons reference and will be confirmed on the Task 9 live run. The clip
**response body** likewise was not captured; success detection (items all `status == 1`) is
reference-derived and confirmed live in Task 9.
