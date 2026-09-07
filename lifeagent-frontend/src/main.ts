import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// 装配全局插件：Pinia 状态 → Vue Router 路由 → Element Plus UI
app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
