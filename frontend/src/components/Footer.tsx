const GITHUB_URL = "https://github.com/"; // TODO: set to the repo URL once it exists

export function Footer() {
  return (
    <footer className="meta border-t border-line">
      <div className="mx-auto flex max-w-[980px] flex-wrap items-center justify-between gap-3 px-4 py-6 text-dim">
        <span className="font-medium text-fg">OfferProof</span>
        <span className="flex gap-5">
          <a href={GITHUB_URL} target="_blank" rel="noreferrer noopener" className="text-dim underline underline-offset-4">
            GitHub
          </a>
          <a href="https://serpapi.com" target="_blank" rel="noreferrer noopener" className="text-dim underline underline-offset-4">
            Built with SerpApi
          </a>
        </span>
      </div>
    </footer>
  );
}
