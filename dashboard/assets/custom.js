window.dash_clientside = Object.assign({}, window.dash_clientside, {
    namespace: {
        displayPage: function(pathname) {
            if (pathname === "/models-impact") {
                return "Models Impact Page Content"; 
            } else if (pathname === "/community-blog") {
                return "Community Blog Page Content";
            } else if (pathname === "/events-publications") {
                return "Events & Publications Page Content";
            } else {
                return "Home Page Content";
            }
        },

        updateSidebarHighlight: function(pathname) {
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
