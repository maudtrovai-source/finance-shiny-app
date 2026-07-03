from shiny import App, ui

# A completely different UI to prove it's a second app
app_ui = ui.page_fluid(
    ui.h1("🚀 App Number 2"),
    ui.p("This is running separately from your Finance App!"),
    ui.input_slider("n", "Choose a number", 1, 100, 50),
    ui.output_text_verbatim("txt"),
)

def server(input, output, session):
    @render.text
    def txt():
        return f"You selected: {input.n()}"

app = App(app_ui, server)