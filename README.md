# Figuarts Tracker

A simple webpage that tracks S.H.Figuarts figures for **JoJo's Bizarre Adventure, One Piece, Bleach, Jujutsu Kaisen, My Hero Academia, and Chainsaw Man** — showing what's on pre-order, what's coming, what's in stock, and what's sold out, with a personal wishlist.

It updates itself once a day automatically using free GitHub tools. No server to run, nothing to pay for.

---

## How it works (the short version)

There are three pieces:

1. **`index.html`** — the webpage itself. It reads a file called `data.json` and displays everything.
2. **`fetch_figures.py`** — a script that pulls fresh figure data from AmiAmi.
3. **`.github/workflows/refresh.yml`** — a built-in GitHub robot that runs the script once a day, saves the fresh data into `data.json`, and updates the site automatically.

You set it up once. After that it runs on its own.

---

## One-time setup (about 10 minutes)

### Step 1 — Create the repository
1. Go to <https://github.com> and sign in (create a free account if needed).
2. Click the **+** in the top-right → **New repository**.
3. Name it something like `figuarts-tracker`.
4. Choose **Public** (required for free GitHub Pages).
5. Click **Create repository**.

### Step 2 — Upload these files
1. On the new repo page, click **uploading an existing file** (or **Add file → Upload files**).
2. Drag in **all** the files from this project, keeping the folder structure:
   - `index.html`
   - `data.json`
   - `fetch_figures.py`
   - `manual_figures.json`
   - the `.github` folder (with `workflows/refresh.yml` inside it)
   - this `README.md`
3. Click **Commit changes**.

> Tip: if dragging the `.github` folder is awkward in the browser, upload the other files first, then use **Add file → Create new file**, type `.github/workflows/refresh.yml` as the name (the slashes create the folders), and paste in the contents of that file.

### Step 3 — Turn on GitHub Pages (this makes the site live)
1. In the repo, go to **Settings** (top menu) → **Pages** (left sidebar).
2. Under **Source**, choose **Deploy from a branch**.
3. Set branch to **main** and folder to **/ (root)**. Click **Save**.
4. Wait 1–2 minutes. The page will show a link like:
   `https://YOUR-USERNAME.github.io/figuarts-tracker/`
5. That link is the app. Bookmark it on your son's phone/computer.

### Step 4 — Turn on the daily auto-update
1. Go to the **Actions** tab in the repo.
2. If it asks you to enable workflows, click **I understand my workflows, enable them**.
3. You'll see a workflow called **"Refresh figure data."** Click it.
4. Click **Run workflow** once to test it immediately (otherwise it waits until the next scheduled time).
5. After it finishes (green checkmark), `data.json` will hold fresh live data, and the site will show it.

That's it. From now on it refreshes every day on its own. You can change how often in `refresh.yml` (the `cron` line).

---

## Using the app

- **Series buttons** at the top filter to one show. The number shows how many figures it has.
- **Status filters** (Pre-Order / Upcoming / In Stock / Sold Out) — click to toggle. Pre-orders and upcoming figures always sort to the top.
- **★ heart** on each figure adds it to the **Wishlist**. The wishlist is saved in that browser (so use the same device/browser to keep it).
- **Search box** finds a character by name.
- **GRID / LIST** toggles the layout.
- **View on AmiAmi** opens the figure's page so you can check the live price and buy.

---

## Keeping it accurate

The daily robot handles most updates. But two things are worth knowing:

**If AmiAmi misses a figure, or you want to fix something by hand**, edit `manual_figures.json`. Add entries in this format (anything you put here overrides or adds to the automatic data):

```json
[
  {
    "id": "my-custom-id",
    "franchise": "jojo",
    "name": "S.H.Figuarts Bruno Bucciarati",
    "status": "preorder",
    "price_jpy": 8800,
    "release_date": "2027-03",
    "image": "",
    "url": "https://www.amiami.com/eng/search/list/?s_keywords=Bruno+Bucciarati"
  }
]
```

- `franchise` must be one of: `jojo`, `onepiece`, `bleach`, `jjk`, `mha`, `csm`
- `status` must be one of: `preorder`, `upcoming`, `available`, `soldout`
- `release_date` is `YYYY-MM` (year-month)

**If the automatic fetch ever stops working** (AmiAmi occasionally changes how their data works), the site won't break or go blank — it just keeps showing the last good data. If that happens, the fix is usually a small update to `fetch_figures.py`. Save this chat; it's easy to patch.

---

## Notes

- Prices are AmiAmi reference prices in Japanese yen, converted to an approximate USD value. **They don't include shipping or US import duties** (as of 2025 the old $800 duty-free allowance on imports ended, so expect some duty on Japan orders).
- Release dates are **Japan** dates; US retailers often list them a month or two later.
- One Punch Man isn't included because Bandai hasn't made S.H.Figuarts figures for it (only figma exist, which is a different brand).
- The figures included on day one are a hand-built starter set; the first successful daily run replaces them with full live data.
