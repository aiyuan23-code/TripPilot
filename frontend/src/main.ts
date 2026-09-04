import { createApp } from 'vue'
import { Alert, Progress } from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

import App from './App.vue'
import router from './router'
import './styles.css'

createApp(App).use(router).use(Alert).use(Progress).mount('#app')
