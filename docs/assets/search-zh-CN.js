// Search the MkDocs section index by substring so Chinese queries need no spaces.
document.addEventListener("DOMContentLoaded", () => {
    const dialog = document.getElementById("mkdocs_search_modal");
    const input = document.getElementById("mkdocs-search-query");
    const results = document.getElementById("mkdocs-search-results");
    const indexURL = new URL(base_url + "/search/search_index.json", document.baseURI);
    const siteURL = new URL("../", indexURL);
    let sections;

    async function search() {
        const query = input.value.trim().toLowerCase();
        results.replaceChildren();
        if (!query) return;
        try {
            if (!sections) {
                sections = fetch(indexURL).then(async response => {
                    if (!response.ok) throw new Error(response.statusText);
                    const index = await response.json();
                    return index.docs.filter(doc => doc.location.split("#")[0].endsWith("zh-CN.html"));
                });
            }
            const entries = await sections;
            if (input.value.trim().toLowerCase() !== query) return;
            results.replaceChildren();
            const terms = query.split(/\s+/);
            const matches = entries.filter(({title, text}) => {
                const content = (title + " " + text).toLowerCase();
                return terms.every(term => content.includes(term));
            });
            matches.sort((a, b) => Number(b.title.toLowerCase().includes(query)) -
                                    Number(a.title.toLowerCase().includes(query)));
            if (!matches.length) results.textContent = results.dataset.noResultsText;
            for (const {title, text, location} of matches) {
                const article = document.createElement("article");
                const heading = document.createElement("h3");
                const link = document.createElement("a");
                link.href = new URL(location, siteURL);
                link.textContent = title;
                heading.append(link);
                const excerpt = document.createElement("p");
                const start = Math.max(0, text.toLowerCase().indexOf(terms[0]) - 40);
                excerpt.textContent = (start ? "…" : "") + text.slice(start, start + 180);
                article.append(heading, excerpt);
                results.append(article);
            }
        } catch {
            sections = undefined;
            results.textContent = "无法加载搜索索引。请确认网站可正常连接；离线阅读时，请使用手册首页提供的本地 HTTP 命令。";
        }
    }
    input.addEventListener("input", search);
    dialog.querySelector("form").addEventListener("submit", event => event.preventDefault());
    const initial = new URLSearchParams(location.search).get("q");
    if (initial) {
        input.value = initial;
        search();
    }
});
