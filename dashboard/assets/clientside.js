window.dash_clientside = Object.assign({}, window.dash_clientside, {
    namespace: {
        // display pages per pathname
        displayPage: async function (pathname) {
            // json version of pages
            const pages = {
                "/models-impact": "/assets/models_impact_page.json",
                "/community-blog": "/assets/community_blog_page.json",
                "/events-publications": "/assets/events_publications_page.json",
            };

            if (pages[pathname]) {
                try {
                    // get path name
                    const response = await fetch(pages[pathname]);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    const layout = await response.json();
                    return layout; 
                } catch (error) {
                    console.error("Error loading page layout:", error);
                    return { type: "Div", props: { children: "Error loading page." } };
                }
            } else {
                // unknown
                return { type: "Div", props: { children: "Page Not Found" } };
            }
        },

        // update sidebar link highlights
        updateSidebarHighlight: function (pathname) {
            const defaultStyle = {
                display: "flex",
                alignItems: "center",
                marginBottom: "10px",
                padding: "5px",
                borderRadius: "5px"
            };
            const highlightedStyle = {
                ...defaultStyle,
                backgroundColor: "#e0e0e0"
            };

            return [
                pathname === "/models-impact" ? highlightedStyle : defaultStyle,
                pathname === "/community-blog" ? highlightedStyle : defaultStyle,
                pathname === "/events-publications" ? highlightedStyle : defaultStyle
            ];
        }
    }
});