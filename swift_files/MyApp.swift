import SwiftUI

@main
struct WrapperApp: App {
    var body: some Scene {
        WindowGroup {
            WebView(url: URL(string: "https://tracker.turnernet.co")!)
                .ignoresSafeArea()
        }
    }
}